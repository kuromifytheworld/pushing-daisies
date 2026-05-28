/* Filter panel wiring — connects UI controls to graph state */

document.addEventListener("DOMContentLoaded", () => {
  // Season buttons
  document.querySelectorAll(".tab-btn[data-season]").forEach(btn => {
    btn.addEventListener("click", () => {
      document.querySelectorAll(".tab-btn[data-season]").forEach(b => b.classList.remove("active"));
      btn.classList.add("active");
      const val = btn.dataset.season;
      state.season  = val === "all" ? null : parseInt(val);
      state.episode = null;
      document.getElementById("episode-slider").value = 0;
      document.getElementById("episode-val").textContent = "All";
      updateEpisodeSliderMax();
      window.applyFilters();
    });
  });

  // Episode slider
  const epSlider = document.getElementById("episode-slider");
  const epVal    = document.getElementById("episode-val");
  epSlider.addEventListener("input", () => {
    const v = parseInt(epSlider.value);
    state.episode = v === 0 ? null : v;
    epVal.textContent = v === 0 ? "All" : `Ep ${v}`;
  });
  epSlider.addEventListener("change", () => window.applyFilters());

  // Relationship type checkboxes
  document.querySelectorAll(".rel-type-check").forEach(cb => {
    cb.addEventListener("change", () => {
      if (cb.checked) {
        state.relTypes.add(cb.value);
      } else {
        state.relTypes.delete(cb.value);
        if (state.relTypes.size === 0) {
          cb.checked = true;
          state.relTypes.add(cb.value);
        }
      }
      window.applyFilters();
    });
  });

  // Min weight slider
  const wtSlider = document.getElementById("weight-slider");
  const wtVal    = document.getElementById("weight-val");
  wtSlider.addEventListener("input", () => {
    state.minWeight = parseInt(wtSlider.value);
    wtVal.textContent = state.minWeight;
  });
  wtSlider.addEventListener("change", () => window.applyFilters());
});

function updateEpisodeSliderMax() {
  const slider = document.getElementById("episode-slider");
  if (!state.season) {
    slider.max = 0;
    slider.value = 0;
    document.getElementById("episode-val").textContent = "All";
    return;
  }
  const maxEp = state.season === 1 ? 9 : 13;
  slider.max = maxEp;
}
