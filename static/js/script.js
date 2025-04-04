let currentSongTitle = '';
let currentArtistName = '';
let currentAlbumArt = '';
let contentLoaded = false;

async function fetchNowPlaying() {
    try {
        const response = await fetch('/now-playing');
        if (response.ok) {
            const data = await response.json();
            console.log("Data received:", data);

            // Preload album art if it's different from the current one
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

        } else {
            console.error('Error fetching now playing:', response.status);
        }
    } catch (error) {
        console.error('Error fetching now playing:', error);
    }
}

// Preload an image and call a callback once it’s loaded
function preloadImage(src, callback) {
    const img = new Image();
    img.src = src;
    img.onload = callback;
}

// Poll every 2 seconds
setInterval(fetchNowPlaying, 2000);

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
