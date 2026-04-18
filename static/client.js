document.addEventListener('DOMContentLoaded', function() {
    var transcriptDiv = document.getElementById('transcript');
    var statusSpan = document.getElementById('status');
    var MAX_PARAGRAPHS = 10;
    var currentPartial = null;

    var params = new URLSearchParams(window.location.search);
    var showPartial = params.get('partial') === 'true';
    var wsUrl = (location.protocol === 'https:' ? 'wss://' : 'ws://')
        + location.host
        + '/ws/transcript/' + SALA
        + (showPartial ? '?partial=true' : '');

    var ws;

    function connect() {
        ws = new WebSocket(wsUrl);

        ws.onopen = function() {
            statusSpan.textContent = 'Connected';
        };

        ws.onmessage = function(event) {
            var msg = JSON.parse(event.data);
            appendTranscript(msg.text, msg.is_partial);
        };

        ws.onclose = function() {
            statusSpan.textContent = 'Disconnected. Reconnecting...';
            setTimeout(connect, 3000);
        };

        ws.onerror = function() {
            statusSpan.textContent = 'Error';
        };
    }

    function appendTranscript(text, isPartial) {
        var trimmed = text.trim();
        if (!trimmed) return;

        if (isPartial) {
            if (!currentPartial) {
                currentPartial = document.createElement('p');
                currentPartial.classList.add('partial');
                transcriptDiv.appendChild(currentPartial);
            }
            currentPartial.textContent = trimmed;
        } else {
            if (currentPartial) {
                currentPartial.remove();
                currentPartial = null;
            }
            var p = document.createElement('p');
            p.textContent = trimmed;
            transcriptDiv.appendChild(p);
        }

        var paragraphs = transcriptDiv.getElementsByTagName('p');
        while (paragraphs.length > MAX_PARAGRAPHS) {
            transcriptDiv.removeChild(paragraphs[0]);
        }

        requestAnimationFrame(function() {
            transcriptDiv.scrollTop = transcriptDiv.scrollHeight;
        });
    }

    connect();
});
