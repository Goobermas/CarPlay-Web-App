let socket = io();
let contentLoaded = false;

socket.on('connect', () => {
    console.log("Connected to Socket.IO");
});

socket.on('track_update', data => {
    console.log("New track received:", data);

    const newSongTitle = data.name;
    const newArtistName = data.artist;
    const newAlbumArt = data.album_art;

    preloadImage(newAlbumArt, () => {
        document.getElementById('album-art').src = newAlbumArt;
        document.querySelector('.background').style.backgroundImage = `url(${newAlbumArt})`;
    });

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
    document.body.addEventListener('click', () => {
        if (document.documentElement.requestFullscreen) {
            document.documentElement.requestFullscreen();
        } else if (document.documentElement.webkitRequestFullscreen) {
            document.documentElement.webkitRequestFullscreen();
        }
    });
});

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
    requestWakeLock();
});
