// YomiMado's ABI adapter for the pinned MIT webview loader implementation.
// Only the two loader entrypoints used by locked wry 0.55.1 are implemented.
#include <webview/detail/platform/windows/webview2/loader.hh>
#include <new>

STDAPI GetAvailableCoreWebView2BrowserVersionString(PCWSTR browser_directory,
                                                   LPWSTR *version) {
  if (!version) {
    return E_POINTER;
  }
  *version = nullptr;
  try {
    webview::detail::mswebview2::loader loader;
    return loader.get_available_browser_version_string(browser_directory, version);
  } catch (const std::bad_alloc &) {
    return E_OUTOFMEMORY;
  } catch (...) {
    return E_FAIL;
  }
}

STDAPI CreateCoreWebView2EnvironmentWithOptions(
    PCWSTR browser_directory, PCWSTR data_directory,
    ICoreWebView2EnvironmentOptions *options,
    ICoreWebView2CreateCoreWebView2EnvironmentCompletedHandler *completed) {
  if (!completed) {
    return E_POINTER;
  }
  try {
    webview::detail::mswebview2::loader loader;
    return loader.create_environment_with_options(browser_directory, data_directory,
                                                  options, completed);
  } catch (const std::bad_alloc &) {
    return E_OUTOFMEMORY;
  } catch (...) {
    return E_FAIL;
  }
}
