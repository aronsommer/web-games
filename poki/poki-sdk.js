// Offline stand-in for the Poki SDK so the archived builds run anywhere:
// no network, ads finish instantly.
(() => {
  // SiteLock in the Unity 2017 builds only accepts Poki hosts or "localhost:<port>";
  // Unity reads the page URL from document.URL.
  Object.defineProperty(document, "URL", {
    value: location.href.replace(location.host, "localhost:8080"),
  });

  // PokiUnitySDK calls these and expects replies via SendMessage to its bridge object
  // (index.html sets window.unityInstance, a promise of it for Unity 2020+ builds).
  let bridge;
  const send = (method, value) =>
    Promise.resolve(window.unityInstance).then((unity) => unity.SendMessage(bridge, method, value));
  window.initPokiBridge = (name) => {
    bridge = name;
    send("ready");
  };
  window.commercialBreak = () => send("commercialBreakCompleted");
  window.rewardedBreak = () => send("rewardedBreakCompleted", "true");

  const noop = () => {};
  window.PokiSDK = {
    gameLoadingStart: noop,
    gameLoadingProgress: noop,
    gameLoadingFinished: noop,
    gameplayStart: noop,
    gameplayStop: noop,
    happyTime: noop,
    roundStart: noop,
    roundEnd: noop,
    customEvent: noop,
    setPlayerAge: noop,
    togglePlayerAdvertisingConsent: noop,
    displayAd: noop,
    destroyAd: noop,
    logError: noop,
    isAdBlocked: () => false,
    getLanguage: () => navigator.language.slice(0, 2),
    getURLParam: (name) => new URLSearchParams(location.search).get(name),
  };
})();
