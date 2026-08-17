  (function () {
    var reduce = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    var ribbon = document.querySelector(".ribbon");

    if (reduce) {
      document.querySelectorAll(".reveal").forEach(function (el) { el.classList.add("seen"); });
      if (ribbon) { ribbon.classList.remove("pending"); }
      return;
    }

    if (!("IntersectionObserver" in window)) {
      document.querySelectorAll(".reveal").forEach(function (el) { el.classList.add("seen"); });
      if (ribbon) { ribbon.classList.remove("pending"); }
      return;
    }

    var io = new IntersectionObserver(function (entries) {
      entries.forEach(function (entry) {
        if (!entry.isIntersecting) { return; }
        entry.target.classList.add("seen");
        io.unobserve(entry.target);
      });
    }, { rootMargin: "0px 0px -12% 0px", threshold: 0.08 });

    document.querySelectorAll(".reveal").forEach(function (el) { io.observe(el); });

    if (ribbon) {
      // Segments grow left to right, staggered, once the schedule is in view.
      var ribbonIO = new IntersectionObserver(function (entries, obs) {
        entries.forEach(function (entry) {
          if (!entry.isIntersecting) { return; }
          Array.prototype.forEach.call(ribbon.children, function (seg, i) {
            seg.style.transitionDelay = i * 110 + "ms";
          });
          ribbon.classList.remove("pending");
          obs.unobserve(entry.target);
        });
      }, { threshold: 0.4 });
      ribbonIO.observe(ribbon);
    }
  })();
