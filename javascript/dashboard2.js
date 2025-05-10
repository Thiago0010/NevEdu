  const percent = 65; // muda esse valor pra o score real
  const circle = document.querySelector('.progress-ring__circle');
  const text = document.getElementById('score-text');

  const radius = 65;
  const circumference = 2 * Math.PI * radius;

  circle.style.strokeDasharray = `${circumference}`;
  const offset = circumference - (percent / 100) * circumference;
  circle.style.strokeDashoffset = offset;

  text.textContent = `${percent}%`;