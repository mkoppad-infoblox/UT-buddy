async function search() {
    const statusColor = {
        "New": "#0ea5e9",           // blue
        "In Progress": "#f59e0b",   // orange
        "Resolved": "#10b981",      // green
        "Closed": "#6b7280"         // gray
    };
    
    const query = document.getElementById("query").value;
    console.log("📤 Sending query:", query);

    try {
        const res = await fetch("/search", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ query })
        });

        if (!res.ok) {
            console.error("❌ Server error:", res.status);
            return;
        }

        const data = await res.json();
        console.log("✅ Got data from server:", data);

        const results = document.getElementById("results");
        results.innerHTML = "";

        if (!data.matches || data.matches.length === 0) {
            results.innerHTML = "<p>No matching tickets found.</p>";
            return;
        }

        results.innerHTML += `<h2>📄 Matching JIRA Tickets with links...</h2>`;

        // Show first 5 results
        const firstFive = data.matches.slice(0, 5);
        const remaining = data.matches.slice(5);

        firstFive.forEach(m => {
            results.innerHTML += `
                <div class='ticket'>
                    <div style="display: flex; justify-content: space-between;">
                        <strong>${m.id}</strong>
                        <span style="color: ${statusColor[m.status] || '#2563eb'}; font-size: 14px;">
    <strong>Status:</strong> ${m.status}
</span>
                       

                    </div>
                    <a href='${m.url}' target='_blank'>${m.title}</a>
                </div>`;
        });

        // If there are more than 5, show "See more" button
        if (remaining.length > 0) {
            const seeMoreBtn = document.createElement("button");
            seeMoreBtn.textContent = "See more related tickets";
            seeMoreBtn.style.marginTop = "15px";
            seeMoreBtn.style.padding = "10px 20px";
            seeMoreBtn.style.backgroundColor = "#2563eb";
            seeMoreBtn.style.color = "#fff";
            seeMoreBtn.style.border = "none";
            seeMoreBtn.style.borderRadius = "8px";
            seeMoreBtn.style.cursor = "pointer";


            seeMoreBtn.addEventListener("click", () => {
                remaining.forEach(m => {
                    results.innerHTML += `
                        <div class='ticket'>
                            <div style="display: flex; justify-content: space-between;">
                                <strong>${m.id}</strong>
                                <span style="color: ${statusColor[m.status] || '#2563eb'}; font-size: 14px;">
    <strong>Status:</strong> ${m.status}
</span>
                            </div>
                            <a href='${m.url}' target='_blank'>${m.title}</a>
                        </div>`;
                });
                seeMoreBtn.remove();
            });

            results.appendChild(seeMoreBtn);
        }

    } catch (e) {
        console.error("⚠️ Fetch failed:", e);
    }
}

document.addEventListener("DOMContentLoaded", function () {
    const btn = document.getElementById("searchBtn");
    if (btn) {
        btn.addEventListener("click", search);
    }
});

