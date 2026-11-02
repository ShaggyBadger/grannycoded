(() => {
  const toggle = document.querySelector("[data-menu-toggle]");
  if (!toggle) return;

  const navigation = document.getElementById(toggle.getAttribute("aria-controls"));
  const label = toggle.querySelector("[data-menu-label]");
  if (!navigation) return;

  const mobileViewport = window.matchMedia("(max-width: 760px)");

  const setMenuOpen = (isOpen) => {
    toggle.setAttribute("aria-expanded", String(isOpen));
    navigation.hidden = mobileViewport.matches && !isOpen;
    if (label) label.textContent = isOpen ? "Close menu" : "Menu";
  };

  const syncViewport = () => {
    toggle.hidden = !mobileViewport.matches;
    if (mobileViewport.matches) {
      setMenuOpen(false);
    } else {
      navigation.hidden = false;
      toggle.setAttribute("aria-expanded", "false");
      if (label) label.textContent = "Menu";
    }
  };

  toggle.addEventListener("click", () => {
    if (!mobileViewport.matches) return;
    setMenuOpen(toggle.getAttribute("aria-expanded") !== "true");
  });

  navigation.addEventListener("click", (event) => {
    if (mobileViewport.matches && event.target.closest("a")) {
      setMenuOpen(false);
    }
  });

  document.addEventListener("keydown", (event) => {
    if (
      event.key === "Escape" &&
      mobileViewport.matches &&
      toggle.getAttribute("aria-expanded") === "true"
    ) {
      setMenuOpen(false);
      toggle.focus();
    }
  });

  if (mobileViewport.addEventListener) {
    mobileViewport.addEventListener("change", syncViewport);
  } else {
    mobileViewport.addListener(syncViewport);
  }

  syncViewport();
})();
