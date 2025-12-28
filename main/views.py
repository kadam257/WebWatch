from django.shortcuts import render, redirect, get_object_or_404
from .models import WatchParty


def index(request):
    watch_parties = WatchParty.objects.all().order_by('-created_at')
    return render(request, 'main/index.html', {
        'watch_parties': watch_parties
    })


def create_party(request):
    if request.method == 'POST':
        name = request.POST.get('name')
        torrent_file = request.FILES.get('torrent_file')

        WatchParty.objects.create(
            name=name,
            torrent_file=torrent_file,
            host_channel_name=''
        )

        return redirect('index')

    return redirect('index')


def watch_party(request, party_id):
    party = get_object_or_404(WatchParty, id=party_id)

    # Hardcoded video path for testing
    video_path = '/media/rapidsave.com_-uz4wq394ml4e1.mp4'

    return render(request, 'main/watch_party.html', {
        'party': party,
        'video_path': video_path
    })
