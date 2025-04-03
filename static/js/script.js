let currentSongTitle = '';
let currentArtistName = '';
let currentAlbumArt = '';
let contentLoaded = false;

const socket = io();

socket.on('connect', () => {
    console.log('Connected to server via WebSocket');
});

socket.on('track_update', data => {
    console.log("Track update received:", data);

    if (data.album_art !== currentAlbumArt) {
        currentAlbumArt = data.album_art;
        preloadImage(currentAlbumArt, () => {
            document.getElementById('album-art').src = currentAlbumArt;
            document.querySelector('.background').style.backgroundImage = `url(${currentAlbumArt})`;
        });
    }

    if (data.name !== currentSongTitle || data.artist !== currentArtistName) {
        currentSongTitle = data.name;
        currentArtistName = data.artist;

        const songTitleElement = document.getElementById('song-title');
        songTitleElement.textContent = currentSongTitle;
        songTitleElement.setAttribute('data-title', currentSongTitle);

        let fontSize = 50;
        if (currentSongTitle.length > 15) {
            const excessChars = currentSongTitle.length - 15;
            fontSize -= excessChars * 1.3;
            fontSize = Math.max(fontSize, 25);
        }
        songTitleElement.style.fontSize = `${fontSize}px`;

        document.getElementById('artist-name').textContent = currentArtistName;
    }

    if (!contentLoaded) {
        document.querySelector('.carplay-container').classList.remove('hidden');
        contentLoaded = true;
    }
});

function preloadImage(src, callback) {
    const img = new Image();
    img.src = src;
    img.onload = callback;
}

let wakeLock = null;

async function requestWakeLock() {
    try {
        wakeLock = await navigator.wakeLock.request('screen');
        console.log("Screen Wake Lock acquired");

        wakeLock.addEventListener('release', () => {
            console.log('Screen Wake Lock released');
            requestWakeLock();
        });
    } catch (err) {
        console.error(`${err.name}, ${err.message}`);
    }
}

document.addEventListener('visibilitychange', () => {
    if (wakeLock !== null && document.visibilityState === 'visible') {
        requestWakeLock();
    }
});

document.addEventListener('DOMContentLoaded', () => {
    document.body.addEventListener('click', () => {
        if (document.documentElement.requestFullscreen) {
            document.documentElement.requestFullscreen();
        } else if (document.documentElement.webkitRequestFullscreen) {
            document.documentElement.webkitRequestFullscreen();
        }
    });
    requestWakeLock();
});
