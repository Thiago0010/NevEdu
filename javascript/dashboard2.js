const percent = 50; // Mude isso futuramente com o score da pessoa
const circle = document.querySelector('.progress-ring__circle');
const text = document.getElementById('score-text');

const radius = circle.r.baseVal.value;
const circumference = 2 * Math.PI * radius;

circle.style.strokeDasharray = `${circumference}`;
circle.style.strokeDashoffset = circumference;

const offset = circumference - (percent / 100) * circumference;
circle.style.strokeDashoffset = offset;

text.textContent = `${percent}%`;   