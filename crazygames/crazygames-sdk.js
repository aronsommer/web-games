// Offline stand-in for the CrazyGames SDK so the archived builds run anywhere:
// no network, ads finish instantly, SDK save data lives in localStorage.
(() => {
  // SiteLock in the games crashes on unknown hosts; Unity reads the page URL from document.URL.
  Object.defineProperty(document, "URL", {
    value: location.href.replace(location.host, "localhost"),
  });

  const later = (fn) => setTimeout(fn);

  // Legacy SDK (Unity 5.6-2019 builds): the game calls window.Crazygames and expects
  // replies via SendMessage to its CrazySDK object (index.html sets window.unityInstance).
  let sdkObject;
  const send = (method, value) =>
    later(() => window.unityInstance.SendMessage(sdkObject, method, value));
  const adEvent = (name) => send("AdEvent", JSON.stringify({ name }));
  window.Crazygames = {
    init(options) {
      sdkObject = options.crazySDKObjectName;
      send("InitCallback", JSON.stringify({ gameLink: location.href }));
      send("AdblockNotDetected");
    },
    requestAd() {
      adEvent("adStarted");
      adEvent("adFinished");
    },
    requestBanners() {},
    requestInviteUrl() {},
    gameplayStart() {},
    gameplayStop() {},
    happytime() {},
  };

  // SDK v3 (Unity 2020+ builds): the game injects sdk.crazygames.com/crazygames-sdk-v3.js and
  // waits for its load event; skip the download and use the stand-in below instead.
  const appendChild = document.head.appendChild.bind(document.head);
  document.head.appendChild = (node) => {
    if (!node.src?.startsWith("https://sdk.crazygames.com/")) return appendChild(node);
    later(() => node.dispatchEvent(new Event("load")));
    return node;
  };

  const prefix = `crazygames-sdk:${location.pathname.replace(/[^/]*$/, "")}:`;
  const noop = () => {};
  const notAvailable = () =>
    Promise.reject({
      code: "userAccountsDisabled",
      message: "Offline archive",
    });
  window.CrazyGames = {
    SDK: {
      environment: "local",
      isQaTool: false,
      init: () => Promise.resolve(),
      ad: {
        requestAd(type, callbacks) {
          later(() => {
            callbacks.adStarted();
            callbacks.adFinished();
          });
        },
        hasAdblock: () => Promise.resolve(false),
      },
      banner: { requestOverlayBanners: noop },
      game: {
        gameplayStart: noop,
        gameplayStop: noop,
        happytime: noop,
        inviteLink: () => location.href,
        showInviteButton: () => location.href,
        hideInviteButton: noop,
      },
      user: {
        isUserAccountAvailable: false,
        systemInfo: {
          countryCode: "",
          locale: navigator.language,
          device: { type: "desktop" },
          os: { name: "", version: "" },
          browser: { name: "", version: "" },
          applicationType: "web",
        },
        addAuthListener: noop,
        addScore: noop,
        getUser: () => Promise.resolve(null),
        getUserToken: notAvailable,
        getXsollaUserToken: notAvailable,
        showAuthPrompt: notAvailable,
        showAccountLinkPrompt: notAvailable,
      },
      data: {
        getItem: (key) => localStorage.getItem(prefix + key),
        setItem: (key, value) => localStorage.setItem(prefix + key, value),
        removeItem: (key) => localStorage.removeItem(prefix + key),
        clear: () =>
          Object.keys(localStorage)
            .filter((key) => key.startsWith(prefix))
            .forEach((key) => localStorage.removeItem(key)),
        syncUnityGameData: noop,
      },
    },
  };
})();
