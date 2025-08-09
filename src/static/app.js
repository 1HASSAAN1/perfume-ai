// Minimal comments, all wired to your API shape { query, params, results }

document.addEventListener("DOMContentLoaded", () => {
  const form = document.getElementById("search-form");
  const input = document.getElementById("search-input");
  const priceCap = document.getElementById("price-cap");
  const topK = document.getElementById("top-k");
  const cheaperOnly = document.getElementById("cheaper-only");
  const resultsDiv = document.getElementById("results");

  form.addEventListener("submit", async (e) => {
    e.preventDefault();

    const name = input.value.trim();
    if (!name) {
      resultsDiv.innerHTML = "<p>Please enter a perfume name.</p>";
      return;
    }

    const params = new URLSearchParams({
      name,
      top_k: topK.value,
      cheaper_than: cheaperOnly.checked ? "true" : "false",
    });
    if (priceCap.value) params.set("price_cap", priceCap.value);

    resultsDiv.innerHTML = "<p>Searching…</p>";

    try {
      const res = await fetch(`/dupes?${params.toString()}`);
      if (!res.ok) {
        const msg = res.status === 404 ? "Not found. Try a different name." : "Server error.";
        resultsDiv.innerHTML = `<p>${msg}</p>`;
        return;
      }
      const data = await res.json(); // {query, params, results}
      const list = data.results || [];

      if (!list.length) {
        resultsDiv.innerHTML = "<p>No dupes matched your filters.</p>";
        return;
      }

      const title = `Similar to ${data.query.name.toLowerCase()} (${data.query.brand?.toLowerCase() || "unknown"})`;
      let html = `<h2>${title}</h2>`;
      html += list
        .map(
          (it) => `
          <div class="card">
            <div class="name"><strong>${it.name}</strong> <span class="brand">by ${it.brand}</span></div>
            <div class="meta">
              <span>Price: ${it.price != null ? "£" + it.price : "N/A"}</span>
              <span>Similarity: ${(it.similarity * 100).toFixed(1)}%</span>
            </div>
          </div>`
        )
        .join("");

      resultsDiv.innerHTML = html;
    } catch (err) {
      console.error(err);
      resultsDiv.innerHTML = "<p>Error fetching results.</p>";
    }
  });
});
