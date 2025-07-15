let debounceTimer;

function debounce(func, delay = 1000) {
  clearTimeout(debounceTimer);
  debounceTimer = setTimeout(() => {
    func();  // ✅ Actually call the function
  }, delay);
}

function extractCommitId(text) {
const commitMatch = text.match(/\b[0-9a-f]{7,40}\b/i);
const releaseMatch = text.match(/\b9\.0\.[0-7]\b/); // Matches 9.0.0 to 9.0.7
return commitMatch ? commitMatch[0] : (releaseMatch ? releaseMatch[0] : null);
}

function appendMessage(content, className) {
	const chat = document.getElementById("chatMessages");
	const msg = document.createElement("div");
	msg.className = className;
	msg.innerHTML = content;
	chat.appendChild(msg);
	chat.scrollTop = chat.scrollHeight;
}

async function searchCommitFailures() {
	const input = document.getElementById("commitInput");
	const userText = input.value.trim();
	if (!userText) return;

	appendMessage(userText, "user-msg");
	input.value = "";

	const commitId = extractCommitId(userText);
	if (!commitId) {
		appendMessage("❗ Please include a valid commit ID in your message.", "bot-msg");
		return;
	}

	try {
		const res = await fetch("/commit_failures", {
			method: "POST",
			headers: { "Content-Type": "application/json" },
			body: JSON.stringify({ commit_id: commitId })
		});

		if (!res.ok) {
			appendMessage(`❌ Server error: ${res.status}`, "bot-msg");
			return;
		}

		const data = await res.json();
		if (!data.matches || data.matches.length === 0) {
			appendMessage("🔍 No matching entries found.", "bot-msg");
			return;
		}

		let response = `<strong>📄 Matching Test Runs:</strong><br>`;
		data.matches.forEach(entry => {
			response += `
				<div style="margin-top: 8px;">
                    <strong>Commit ID: </strong> ${entry.Revision}<br>
					<strong>Date:</strong> ${entry.Date}<br>
					<strong>Type:</strong> ${entry.Type}<br>
					<strong>Status:</strong> ${entry.Status}<br>
					<strong>Total:</strong> ${entry.Total}<br>
					<strong>Failures:</strong> ${entry.Failures}<br>
					<strong>Garbage:</strong> ${entry.Garbage}<br>
					<a href="${entry.id_href}" target="_blank">🔗 View Run</a>
				</div><hr>`;
		});

		appendMessage(response, "bot-msg");

	} catch (err) {
		console.error("Error:", err);
		appendMessage("⚠️ Something went wrong. Please try again.", "bot-msg");
	}
}

document.addEventListener("DOMContentLoaded", () => {
	const btn = document.getElementById("commitSearchBtn");
	const input = document.getElementById("commitInput");

	btn.addEventListener("click", searchCommitFailures);
	input.addEventListener("keypress", e => {
		if (e.key === "Enter") {
			e.preventDefault();
			searchCommitFailures();
		}
	});
});

function initAccordion() {
  const acc = document.getElementsByClassName("accordion");
  for (let i = 0; i < acc.length; i++) {
    acc[i].addEventListener("click", function () {
      this.classList.toggle("active");
      const panel = this.nextElementSibling;
      panel.style.maxHeight = panel.style.maxHeight ? null : panel.scrollHeight + "px";
    });
  }
}

document.addEventListener("DOMContentLoaded", () => {
  const btn = document.getElementById("commitSearchBtn");
  if (btn) {
    btn.addEventListener("click", () => debounce(searchCommitFailures, 200));
  }
});
