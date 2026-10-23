// 외부 라이브러리 없이 사용하는 작은 우주 인터랙션입니다.
const cosmicMessage = document.getElementById("cosmic-message");
const planetButton = document.getElementById("planet-wish");
const messageButton = document.getElementById("new-message");
const motionButton = document.getElementById("motion-toggle");
const messagePanel = document.querySelector(".space-message");
const messages = [
  "서두르지 않아도 괜찮아요. 당신은 당신의 궤도를 돌고 있으니까요.",
  "멀리 있는 별도 누군가에게는 가장 밝은 빛이에요. 당신처럼요.",
  "오늘 보낸 작은 인사가, 누군가의 긴 밤을 밝혀줄지도 몰라요.",
  "조금 돌아가는 길에도, 처음 만나는 별자리가 있어요.",
  "우주가 이렇게 넓은데, 여기서 만난 건 꽤 근사한 우연이에요.",
  "잠깐 쉬어가도 괜찮아요. 별들도 낮에는 보이지 않으니까요.",
];
let messageIndex = 0;
let glowTimer;

function receiveMessage() {
  // 같은 문구가 연속으로 나오지 않게 다음 별을 고릅니다.
  messageIndex = (messageIndex + 1 + Math.floor(Math.random() * (messages.length - 1))) % messages.length;
  cosmicMessage.textContent = messages[messageIndex];
  const scene = document.querySelector(".orbit-scene");
  scene.classList.remove("wish-sent");
  clearTimeout(glowTimer);
  requestAnimationFrame(() => {
    scene.classList.add("wish-sent");
    glowTimer = setTimeout(() => scene.classList.remove("wish-sent"), 1200);
  });
}

if (planetButton && messageButton && cosmicMessage && messagePanel) {
  planetButton.hidden = false;
  messagePanel.hidden = false;
  planetButton.addEventListener("click", receiveMessage);
  messageButton.addEventListener("click", receiveMessage);
}

if (motionButton) {
  const motionPreference = window.matchMedia("(prefers-reduced-motion: reduce)");
  function syncMotionPreference() {
    motionButton.hidden = motionPreference.matches;
  }
  syncMotionPreference();
  motionPreference.addEventListener("change", syncMotionPreference);
  motionButton.addEventListener("click", () => {
    const paused = document.body.classList.toggle("motion-paused");
    motionButton.setAttribute("aria-pressed", String(paused));
    motionButton.textContent = paused ? "움직임 재생하기 ▷" : "움직임 멈추기 Ⅱ";
  });
}
