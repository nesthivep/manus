const tank = document.getElementById('tank');
const gameArea = document.getElementById('game-area');

let tankX = 375;
let tankY = 550;

document.addEventListener('keydown', (event) => {
    switch(event.key) {
        case 'ArrowLeft':
            tankX -= 10;
            break;
        case 'ArrowRight':
            tankX += 10;
            break;
        case 'ArrowUp':
            tankY -= 10;
            break;
        case 'ArrowDown':
            tankY += 10;
            break;
    }
    tank.style.left = `${tankX}px`;
    tank.style.bottom = `${tankY}px`;
});