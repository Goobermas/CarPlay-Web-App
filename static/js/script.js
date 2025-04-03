let currentSongTitle = '';
let currentArtistName = '';
let currentAlbumArt = '';
let contentLoaded = false;

// Connect to WebSocket server
const socket = io();

// Handle incoming track updates
socket.on('track_update', (data) => {
    console.log("Now playing:", data);

    // Update album art if changed
    if (data.album_art !== currentAlbumArt) {
        currentAlbumArt = data.album_art;
        preloadImage(currentAlbumArt, () => {
            document.getElementById('album-art').src = currentAlbumArt;
            document.querySelector('.background').style.backgroundImage = `url(${currentAlbumArt})`;
        });
    }

    const newSongTitle = data.name;
    const newArtistName = data.artist;

    if (newSongTitle !== currentSongTitle || newArtistName !== currentArtistName) {
        currentSongTitle = newSongTitle;
        currentArtistName = newArtistName;

        const songTitleElement = document.getElementById('song-title');
        songTitleElement.textContent = newSongTitle;
        songTitleElement.setAttribute('data-title', newSongTitle);

        let fontSize = 50;
        if (newSongTitle.length > 15) {
            const excessChars = newSongTitle.length - 15;
            fontSize -= excessChars * 1.3;
            fontSize = Math.max(fontSize, 25);
        }
        songTitleElement.style.fontSize = `${fontSize}px`;

        document.getElementById('artist-name').textContent = newArtistName;
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

document.addEventListener('DOMContentLoaded', () => {
    // One-click fullscreen
    document.body.addEventListener('click', () => {
        const docEl = document.documentElement;
        if (docEl.requestFullscreen) docEl.requestFullscreen();
        else if (docEl.webkitRequestFullscreen) docEl.webkitRequestFullscreen();
    });

    // Wake lock
    requestWakeLock();
});

let wakeLock = null;

async function requestWakeLock() {
    try {
        wakeLock = await navigator.wakeLock.request('screen');
        console.log("Screen Wake Lock acquired");

        wakeLock.addEventListener('release', () => {
            console.log('Screen Wake Lock released');
            requestWakeLock(); // Try again when released
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
