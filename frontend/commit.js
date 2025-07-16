let debounceTimer;

function debounce(func, delay = 1000) {
  clearTimeout(debounceTimer);
  debounceTimer = setTimeout(() => {
    func();  // ✅ Actually call the function
  }, delay);
}

function extractCommitId(text) {
	const commitMatch = text.match(/\b[0-9a-f]{7,40}\b/i);
	const releaseMatch = text.match(/9\.0\.[0-7]/);
	return commitMatch ? commitMatch[0] : (releaseMatch ? releaseMatch[0] : null);
}


function extractDateRange(text) {
	// Match range: YYYY-MM-DD to YYYY-MM-DD
	// Match two dates separated by any word(s) (e.g., 'to', 'and', 'until', etc.)
	const dateRangeMatch = text.match(/(\d{4}-\d{2}-\d{2})\s+\w+\s+(\d{4}-\d{2}-\d{2})/i);
	if (dateRangeMatch) {
		return {
			start: dateRangeMatch[1],
			end: dateRangeMatch[2]
		};
	}
	// Match single date: YYYY-MM-DD
	const singleDateMatch = text.match(/\b(\d{4}-\d{2}-\d{2})\b/);
	if (singleDateMatch) {
		return {
			start: singleDateMatch[1],
			end: singleDateMatch[1]
		};
	}
	return null;
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

		// Check for date range, commit id, or author name (exact word match only)
		const dateRange = extractDateRange(userText);
						let commitId = extractCommitId(userText);
						// Regex for release string anywhere in input (e.g., 'give me the test run for 9.0.1')
						const releasePattern = /\b9\.0\.[0-7]\b/;
						let isReleaseString = false;
						let isValidCommitId = false;
						// Always treat a release string as a valid commit id, even if extractCommitId fails
						const releaseMatch = userText.match(releasePattern);
						if (releaseMatch) {
							commitId = releaseMatch[0];
							isReleaseString = true;
						}
						if (commitId) {
							if (isReleaseString || commitId.length === 7 || commitId.length === 40) {
								isValidCommitId = true;
							} else {
								appendMessage("❗ Please enter a valid commit ID (7 or 40 characters, or a valid release like 9.0.0).", "bot-msg");
								return;
							}
						}
				let isAuthorName = false;
				let authorNameWord = null;
				let authorFullName = null;
				if (!commitId && !dateRange && userText.length > 1) {
					if (!userText.includes(" ")) {
						// Single word
						isAuthorName = true;
						authorNameWord = userText.trim();
					} else {
						// Multi-word: treat as full name
						isAuthorName = true;
						authorFullName = userText.trim();
					}
				}

			if (!dateRange && !isAuthorName && !isValidCommitId) {
				appendMessage("❗ Please include a valid name, commit id, or date (YYYY-MM-DD to YYYY-MM-DD) in your message.", "bot-msg");
				return;
			}

	try {
		let body = {};
		if (dateRange) {
			body = { start_date: dateRange.start, end_date: dateRange.end, raw_query: userText };
		} else if (commitId && isValidCommitId) {
			body = { commit_id: commitId, raw_query: userText };
		} else if (isAuthorName) {
			body = { author_name: userText.trim(), raw_query: userText };
		}

		const res = await fetch("/commit_failures", {
			method: "POST",
			headers: { "Content-Type": "application/json" },
			body: JSON.stringify(body)
		});

		if (!res.ok) {
			appendMessage(`❌ Server error: ${res.status}`, "bot-msg");
			return;
		}

		const data = await res.json();
					if (!data.matches || data.matches.length === 0) {
						if (dateRange) {
							appendMessage("🔍 No entries found in the specified date range.", "bot-msg");
						} else if (isAuthorName) {
							appendMessage("🔍 No entries found for the given author name.", "bot-msg");
						} else if (commitId && isValidCommitId) {
							appendMessage("❗ Invalid commit ID: not found in database.", "bot-msg");
						} else {
							appendMessage("❗ Please include a valid name, commit id, or date (YYYY-MM-DD to YYYY-MM-DD) in your message.", "bot-msg");
						}
						return;
					}

				// If date range, filter results by date
				let filteredMatches = data.matches;
				if (dateRange) {
					const start = new Date(dateRange.start);
					const end = new Date(dateRange.end);
					filteredMatches = data.matches.filter(entry => {
						const entryDate = new Date(entry.Date);
						return entryDate >= start && entryDate <= end;
					});
					if (filteredMatches.length === 0) {
						appendMessage("🔍 No entries found in the specified date range.", "bot-msg");
						return;
					}
				}
				// If commitId, filter for exact match (7 or 40 chars)
				// Only apply commit ID filtering if not a release string
				if (commitId && isValidCommitId && !isReleaseString) {
					filteredMatches = filteredMatches.filter(entry => {
						if (!entry.Revision) return false;
						if (commitId.length === 7) {
							return entry.Revision.startsWith(commitId);
						} else if (commitId.length === 40) {
							return entry.Revision === commitId;
						}
						return false;
					});
					if (filteredMatches.length === 0) {
						appendMessage("❗ Invalid commit ID: not found in database.", "bot-msg");
						return;
					}
				}
				// If author name, filter for exact word or full name match in author_name
						if (isAuthorName && (authorNameWord || authorFullName)) {
							filteredMatches = filteredMatches.filter(entry => {
								if (!entry.author_name) return false;
								const entryName = entry.author_name.trim().toLowerCase();
								if (authorFullName) {
									// Full name match (all words, in order, case-insensitive)
									return entryName === authorFullName.toLowerCase();
								} else if (authorNameWord) {
									// Partial match for first name (first word in author_name)
									const firstWord = entryName.split(/\s+/)[0];
									if (firstWord.startsWith(authorNameWord.toLowerCase())) {
										return true;
									}
									// Otherwise, require exact match for any word
									return entryName.split(/\s+/).some(word => word === authorNameWord.toLowerCase());
								}
								return false;
							});
							if (filteredMatches.length === 0) {
								appendMessage("🔍 No entries found for the given author name.", "bot-msg");
								return;
							}
						}

		var response = '<strong>📄 Matching Test Runs:</strong><br>';
		// Sort Jenkins first
		var jenkinsResults = filteredMatches.filter(function(entry) { return entry.Source === "Jenkins"; });
		var testCenterResults = filteredMatches.filter(function(entry) { return entry.Source !== "Jenkins"; });
		var safe = function(val) { return (val !== undefined && val !== null ? val : "N/A"); };

		jenkinsResults.forEach(function(entry) {
			response +=
				'<div style="margin-top: 8px;">' +
				'<strong>Commit ID:</strong> ' + safe(entry.Revision) + '<br>' +
				'<strong>Date:</strong> ' + safe(entry.Date) + '<br>' +
				'<strong>Type:</strong> ' + safe(entry.Type) + '<br>' +
				'<strong>Status:</strong> ' + safe(entry.Status) + '<br>' +
				'<strong>Total:</strong> ' + safe(entry.Total) + '<br>' +
				'<strong>Passed:</strong> ' + safe(entry.Passed) + '<br>' +
				'<strong>Failed:</strong> ' + safe(entry.Failed) + '<br>' +
				'<strong>Skipped:</strong> ' + safe(entry.Skipped) + '<br>' +
				'<strong>Platform:</strong> ' + safe(entry.Platform) + '<br>' +
				'<strong>Author Name:</strong> ' + safe(entry.author_name) + '<br>' +
				'<strong>Author Email:</strong> ' + safe(entry.author_email) + '<br>' +
				'<a href="' + safe(entry.URL) + '" target="_blank">🔗 View Run</a>' +
				'</div><hr>';
		});
		testCenterResults.forEach(function(entry) {
			var total = Number(entry.Total) || 0;
			var failures = Number(entry.Failures) || 0;
			var passed = total - failures;
			response +=
				'<div style="margin-top: 8px;">' +
				'<strong>Commit ID:</strong> ' + safe(entry.Revision) + '<br>' +
				'<strong>Date:</strong> ' + safe(entry.Date) + '<br>' +
				'<strong>Type:</strong> ' + safe(entry.Type) + '<br>' +
				'<strong>Status:</strong> ' + safe(entry.Status) + '<br>' +
				'<strong>Total:</strong> ' + safe(entry.Total) + '<br>' +
				'<strong>Passed:</strong> ' + safe(passed) + '<br>' +
				'<strong>Failed:</strong> ' + safe(entry.Failures) + '<br>' +
				'<strong>Garbage:</strong> ' + safe(entry.Garbage) + '<br>' +
				'<strong>Platform:</strong> ' + safe(entry.Platform) + '<br>' +
				'<strong>Author Name:</strong> ' + safe(entry.author_name) + '<br>' +
				'<strong>Author Email:</strong> ' + safe(entry.author_email) + '<br>' +
				'<a href="' + safe(entry.id_href) + '" target="_blank">🔗 View Run</a>' +
				'</div><hr>';
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
