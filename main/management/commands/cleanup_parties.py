from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
from main.models import WatchParty


class Command(BaseCommand):
    help = 'Clean up watch parties with no participants for more than 10 minutes'

    def handle(self, *args, **options):
        # Find parties with 0 participants and last activity > 10 minutes ago
        cutoff_time = timezone.now() - timedelta(minutes=10)

        old_parties = WatchParty.objects.filter(
            participant_count=0,
            last_activity__lt=cutoff_time
        )

        count = old_parties.count()

        if count > 0:
            self.stdout.write(f'Deleting {count} inactive watch parties...')
            old_parties.delete()
            self.stdout.write(self.style.SUCCESS(f'Successfully deleted {count} watch parties'))
        else:
            self.stdout.write('No inactive watch parties to delete')
