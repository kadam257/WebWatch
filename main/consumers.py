import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from .models import WatchParty


class WatchPartyConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.party_id = self.scope['url_route']['kwargs']['party_id']
        self.room_group_name = f'watch_party_{self.party_id}'
        self.is_host = False

        # Join room group
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )

        await self.accept()

        # Check if this user should be the host
        party = await self.get_party()
        if not party.host_channel_name:
            # First person to join becomes host
            await self.set_host(party)
            self.is_host = True

        # Increment participant count
        participant_count = await self.increment_participant_count()

        # Send welcome message with host status
        await self.send(text_data=json.dumps({
            'type': 'connection_established',
            'message': 'Connected to watch party',
            'is_host': self.is_host,
            'participant_count': participant_count
        }))

        # Notify others that someone joined
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'user_joined',
                'channel_name': self.channel_name,
                'participant_count': participant_count
            }
        )

    async def disconnect(self, close_code):
        # Decrement participant count
        participant_count = await self.decrement_participant_count()

        # If host is leaving, clear host status
        if self.is_host:
            await self.clear_host()

        # Notify others that someone left
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'user_left',
                'participant_count': participant_count
            }
        )

        # Leave room group
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )

    async def receive(self, text_data):
        data = json.loads(text_data)
        message_type = data.get('type')

        # Only allow host to send playback control messages
        if message_type in ['play', 'pause', 'seek']:
            if not self.is_host:
                await self.send(text_data=json.dumps({
                    'type': 'error',
                    'message': 'Only the host can control playback'
                }))
                return

        # Handle viewer requests for re-sync
        if message_type in ['viewer_play_request', 'viewer_seek_request']:
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'request_state',
                    'requester': self.channel_name
                }
            )
            return

        # Handle periodic sync check from viewer
        if message_type == 'viewer_sync_check':
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'request_sync_check',
                    'requester': self.channel_name
                }
            )
            return

        # Handle sync check response from host
        if message_type == 'sync_check_response':
            await self.channel_layer.send(
                data['requester'],
                {
                    'type': 'send_sync_check',
                    'time': data['time']
                }
            )
            return

        # Handle state response from host
        if message_type == 'state_response':
            # Forward state to the requester
            await self.channel_layer.send(
                data['requester'],
                {
                    'type': 'sync_state',
                    'state': data['state']
                }
            )
            return

        # Broadcast message to room group
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'party_message',
                'message': data,
                'sender': self.channel_name
            }
        )

    async def party_message(self, event):
        message = event['message']
        sender = event.get('sender')

        # Don't send the message back to the sender
        if sender != self.channel_name:
            await self.send(text_data=json.dumps(message))

    async def user_joined(self, event):
        # Notify this user that someone joined (but not themselves)
        if event['channel_name'] != self.channel_name:
            await self.send(text_data=json.dumps({
                'type': 'user_joined',
                'message': 'A user joined the party',
                'participant_count': event['participant_count']
            }))

    async def user_left(self, event):
        # Notify that someone left
        await self.send(text_data=json.dumps({
            'type': 'user_left',
            'message': 'A user left the party',
            'participant_count': event['participant_count']
        }))

    async def request_state(self, event):
        # Only host responds to state requests
        if self.is_host:
            await self.send(text_data=json.dumps({
                'type': 'state_request',
                'requester': event['requester']
            }))

    async def sync_state(self, event):
        # Receive state sync from host
        await self.send(text_data=json.dumps({
            'type': 'sync_state',
            'state': event['state']
        }))

    async def request_sync_check(self, event):
        # Only host responds to periodic sync checks
        if self.is_host:
            await self.send(text_data=json.dumps({
                'type': 'sync_check_request',
                'requester': event['requester']
            }))

    async def send_sync_check(self, event):
        # Viewers receive periodic sync check with current time
        await self.send(text_data=json.dumps({
            'type': 'sync_check',
            'time': event['time']
        }))

    @database_sync_to_async
    def get_party(self):
        return WatchParty.objects.get(id=self.party_id)

    @database_sync_to_async
    def set_host(self, party):
        party.host_channel_name = self.channel_name
        party.save()

    @database_sync_to_async
    def clear_host(self):
        party = WatchParty.objects.get(id=self.party_id)
        party.host_channel_name = ''
        party.save()

    @database_sync_to_async
    def increment_participant_count(self):
        party = WatchParty.objects.get(id=self.party_id)
        party.participant_count += 1
        party.save()
        return party.participant_count

    @database_sync_to_async
    def decrement_participant_count(self):
        party = WatchParty.objects.get(id=self.party_id)
        party.participant_count = max(0, party.participant_count - 1)
        party.save()
        return party.participant_count
