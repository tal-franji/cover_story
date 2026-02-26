let gameState = {
    grid: [],
    pieces: [],
    boardRect: null,
    imageB64: null,
    colors: ['#e67e22', '#2ecc71', '#f1c40f', '#3498db', '#ecf0f1']
};

document.getElementById('file-upload').addEventListener('change', async (e) => {
    const file = e.target.files[0];
    if (!file) return;

    const formData = new FormData();
    formData.append('image', file);

    document.getElementById('upload-section').innerHTML = 'Processing Image...';

    try {
        const response = await fetch('/analyze', {
            method: 'POST',
            body: formData
        });
        const result = await response.json();

        if (result.error) {
            alert(result.error);
            location.reload();
            return;
        }

        gameState.grid = result.grid;
        gameState.clusterColors = result.cluster_colors.map(rgb => `rgb(${rgb[2]}, ${rgb[1]}, ${rgb[0]})`);
        gameState.pieces = result.pieces;
        gameState.boardRect = result.board_rect;
        gameState.imageB64 = result.image_b64;

        renderGrid();
        renderPieces();
        document.getElementById('piece-info').innerText = `Detected ${gameState.pieces.length} pieces. (Expected blocks: 25, Found: ${gameState.pieces.reduce((sum, p) => sum + p.length, 0)})`;
        document.getElementById('status-message').innerText = '';
        document.getElementById('verification-section').style.display = 'block';
        document.getElementById('upload-section').style.display = 'none';

    } catch (err) {
        console.error(err);
        alert('Error processing image');
    }
});

function renderGrid() {
    const container = document.getElementById('grid-container');
    container.innerHTML = '';

    gameState.grid.forEach((row, r) => {
        row.forEach((colorIdx, c) => {
            const cell = document.createElement('div');
            cell.className = `cell color-${colorIdx}`;
            cell.style.backgroundColor = gameState.clusterColors[colorIdx];
            cell.dataset.r = r;
            cell.dataset.c = c;
            cell.addEventListener('click', () => {
                const newIdx = (gameState.grid[r][c] + 1) % gameState.clusterColors.length;
                gameState.grid[r][c] = newIdx;
                cell.className = `cell color-${newIdx}`;
                cell.style.backgroundColor = gameState.clusterColors[newIdx];
            });
            container.appendChild(cell);
        });
    });
}

function renderPieces() {
    const container = document.getElementById('pieces-preview');
    container.innerHTML = '';

    gameState.pieces.forEach(p => {
        const preview = document.createElement('div');
        preview.className = 'piece-preview';

        const maxR = Math.max(...p.map(c => c[0]));
        const maxC = Math.max(...p.map(c => c[1]));

        preview.style.gridTemplateRows = `repeat(${maxR + 1}, 15px)`;
        preview.style.gridTemplateColumns = `repeat(${maxC + 1}, 15px)`;

        for (let r = 0; r <= maxR; r++) {
            for (let c = 0; c <= maxC; c++) {
                const cell = document.createElement('div');
                const isPart = p.some(coord => coord[0] === r && coord[1] === c);
                cell.className = isPart ? 'p-cell' : 'p-empty';
                preview.appendChild(cell);
            }
        }
        container.appendChild(preview);
    });
}

document.getElementById('solve-btn').addEventListener('click', () => triggerSolve(false));
document.getElementById('hint-btn').addEventListener('click', () => triggerSolve(true));

async function triggerSolve(isHint) {
    const status = document.getElementById('status-message');
    status.innerText = isHint ? 'Finding a hint...' : 'Solving... (this may take a few seconds)';
    status.style.color = '#3498db';

    try {
        const response = await fetch('/solve', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                grid: gameState.grid,
                pieces: gameState.pieces
            })
        });

        const result = await response.json();
        if (result.error) {
            status.innerText = `Solver Error: ${result.error}`;
            status.style.color = '#e74c3c';
            return;
        }

        status.innerText = isHint ? 'Hint ready!' : 'Solution Found!';
        status.style.color = '#2ecc71';
        renderSolution(result.solution, isHint);
    } catch (err) {
        status.innerText = 'Server error or no connection.';
        status.style.color = '#e74c3c';
    }
}

function renderSolution(placements, isHint = false) {
    document.getElementById('verification-section').style.display = 'none';
    document.getElementById('solution-section').style.display = 'block';

    const canvas = document.getElementById('solution-canvas');
    const ctx = canvas.getContext('2d');
    const img = new Image();

    img.onload = () => {
        canvas.width = img.width;
        canvas.height = img.height;
        ctx.drawImage(img, 0, 0);

        if (!gameState.boardRect) return;

        const [bx, by, bw, bh] = gameState.boardRect;
        const cellW = bw / 5;
        const cellH = bh / 5;

        // Optionally only render the first piece if it's a hint
        const piecesToRender = isHint ? [placements[0]] : placements;

        piecesToRender.forEach((p, idx) => {
            const colors = [
                '#e74c3c', '#3498db', '#f1c40f', '#2ecc71', '#9b59b6',
                '#e67e22', '#fd79a8', '#1abc9c', '#f39c12', '#d35400'
            ];
            const color = colors[idx % colors.length];

            ctx.fillStyle = color + '99'; // 60% opacity hex
            ctx.strokeStyle = color;
            ctx.lineWidth = 4;
            ctx.lineJoin = 'round';

            const margin = 2; // Small global margin for the whole piece

            // 1. Draw solid blocks (Fill)
            p.coords.forEach(([r, c]) => {
                const rx = bx + c * cellW + margin;
                const ry = by + r * cellH + margin;
                ctx.fillRect(rx, ry, cellW - 2 * margin, cellH - 2 * margin);
            });

            // 2. Draw external contour (Borders)
            ctx.beginPath();
            p.coords.forEach(([r, c]) => {
                const rx = bx + c * cellW + margin;
                const ry = by + r * cellH + margin;
                const rw = cellW - 2 * margin;
                const rh = cellH - 2 * margin;

                // Check Top neighbor
                if (!p.coords.some(cc => cc[0] === r - 1 && cc[1] === c)) {
                    ctx.moveTo(rx, ry);
                    ctx.lineTo(rx + rw, ry);
                }
                // Check Bottom neighbor
                if (!p.coords.some(cc => cc[0] === r + 1 && cc[1] === c)) {
                    ctx.moveTo(rx, ry + rh);
                    ctx.lineTo(rx + rw, ry + rh);
                }
                // Check Left neighbor
                if (!p.coords.some(cc => cc[1] === c - 1 && cc[0] === r)) {
                    ctx.moveTo(rx, ry);
                    ctx.lineTo(rx, ry + rh);
                }
                // Check Right neighbor
                if (!p.coords.some(cc => cc[1] === c + 1 && cc[0] === r)) {
                    ctx.moveTo(rx + rw, ry);
                    ctx.lineTo(rx + rw, ry + rh);
                }
            });
            ctx.stroke();
        });
    };

    img.src = `data:image/jpeg;base64,${gameState.imageB64}`;
}

document.getElementById('reset-btn').addEventListener('click', () => location.reload());
