document.addEventListener("DOMContentLoaded", function () {
    // Dynamic Greeting
    const hour = new Date().getHours();
    let greeting = "Hello";
    if (hour >= 5 && hour < 12) greeting = "Good Morning";
    else if (hour >= 12 && hour < 17) greeting = "Good Afternoon";
    else if (hour >= 17 && hour < 21) greeting = "Good Evening";
    else greeting = "Good Night";
    document.getElementById("greeting-text").innerText = `${greeting}, friend!`;
  
    // Bot animation
    lottie.loadAnimation({
      container: document.getElementById('utbot-animation'),
      renderer: 'svg',
      loop: true,
      autoplay: true,
      path: 'https://assets10.lottiefiles.com/packages/lf20_mzrqh3pc.json'
    });
  
    // Remove bubble after 5 seconds
    setTimeout(() => {
      const bubble = document.getElementById("utbot-speech");
      if (bubble) bubble.style.display = "none";
    }, 5000);
  
    // Animate cards
    const cards = document.querySelectorAll('.card');
    const observer = new IntersectionObserver(entries => {
      entries.forEach(entry => {
        if (entry.isIntersecting) {
          entry.target.style.opacity = 1;
          observer.unobserve(entry.target);
        }
      });
    }, { threshold: 0.1 });
    cards.forEach(card => {
      card.style.opacity = 0;
      observer.observe(card);
    });
  
    // Typewriter effect
    const text = "Your all-in-one assistant for debugging and resolving unit test failures. Powered by AI and integrated with JIRA, NIOS test runs, and smart resolution suggestions.";
    const speed = 30;
    let i = 0;
    const target = document.getElementById("typewriter");
  
    function typeWriter() {
      if (!target || i >= text.length) return;
      target.innerHTML += text.charAt(i);
      i++;
      if (i === text.length) {
        setTimeout(showEmoji, 300);
      } else {
        setTimeout(typeWriter, speed);
      }
    }
  
    function showEmoji() {
      const emoji = document.createElement("span");
      emoji.textContent = " 🔍";
      emoji.classList.add("bouncing-emoji");
      target.appendChild(emoji);
    }
  
    typeWriter();
  
    // Inactivity reminder
    let inactivityTimer;
    const intro_ = document.querySelector(".intro");
    function showHelpMessage() {
      if (intro_ && !document.getElementById("help-message")) {
        const helpMsg = document.createElement("p");
        helpMsg.id = "help-message";
        helpMsg.innerText = "💬 Need help? Try the UT Buddy Assistant!";
        helpMsg.style.marginTop = "20px";
        helpMsg.style.color = "#cbd5e1";
        helpMsg.style.textAlign = "center";
        helpMsg.style.opacity = "0";
        helpMsg.style.transition = "opacity 0.5s ease";
        intro_.appendChild(helpMsg);
        requestAnimationFrame(() => {
          helpMsg.style.opacity = "1";
        });
      }
    }
  
    function resetInactivityTimer() {
      clearTimeout(inactivityTimer);
      inactivityTimer = setTimeout(showHelpMessage, 15000);
    }
  
    ["mousemove", "keydown", "scroll", "touchstart"].forEach(event => {
      document.addEventListener(event, resetInactivityTimer);
    });
  
    resetInactivityTimer();
  });
