// Isolated compatibility probe; this is not linked into YomiMado yet.
#include <webview/detail/platform/windows/webview2/loader.hh>
#include <wrl.h>
#include <chrono>
#include <iostream>

using Microsoft::WRL::Callback;
using Microsoft::WRL::ComPtr;

int wmain(int argc, wchar_t **argv) {
  if (argc != 2 || FAILED(CoInitializeEx(nullptr, COINIT_APARTMENTTHREADED))) {
    return 1;
  }
  webview::detail::mswebview2::loader loader;
  LPWSTR version = nullptr;
  HRESULT result = loader.get_available_browser_version_string(nullptr, &version);
  if (FAILED(result) || !version || !*version) {
    std::cerr << "Installed Evergreen discovery failed: " << std::hex << result;
    return 2;
  }
  std::wcout << L"Evergreen version: " << version << std::endl;
  CoTaskMemFree(version);
  if (GetModuleHandleW(L"WebView2Loader.dll")) {
    std::cerr << "Microsoft SDK loader unexpectedly loaded";
    return 3;
  }
  HWND window = CreateWindowExW(0, L"STATIC", L"YomiMado loader probe",
                               WS_OVERLAPPEDWINDOW, 0, 0, 640, 480,
                               nullptr, nullptr, GetModuleHandleW(nullptr), nullptr);
  if (!window) {
    return 4;
  }
  bool complete = false;
  HRESULT asynchronous = E_PENDING;
  ComPtr<ICoreWebView2Environment> environment;
  ComPtr<ICoreWebView2Controller> controller;
  auto created = Callback<ICoreWebView2CreateCoreWebView2EnvironmentCompletedHandler>(
      [&](HRESULT error, ICoreWebView2Environment *value) -> HRESULT {
        asynchronous = error;
        if (FAILED(error) || !value) {
          complete = true;
          return S_OK;
        }
        environment = value;
        auto controlled = Callback<ICoreWebView2CreateCoreWebView2ControllerCompletedHandler>(
            [&](HRESULT error, ICoreWebView2Controller *value) -> HRESULT {
              asynchronous = error;
              controller = value;
              complete = true;
              return S_OK;
            });
        asynchronous = environment->CreateCoreWebView2Controller(window, controlled.Get());
        if (FAILED(asynchronous)) {
          complete = true;
        }
        return S_OK;
      });
  result = loader.create_environment_with_options(nullptr, argv[1], nullptr, created.Get());
  if (FAILED(result)) {
    std::cerr << "Environment call failed: " << std::hex << result;
    return 5;
  }
  const auto deadline = std::chrono::steady_clock::now() + std::chrono::seconds(40);
  while (!complete && std::chrono::steady_clock::now() < deadline) {
    MSG message;
    while (PeekMessageW(&message, nullptr, 0, 0, PM_REMOVE)) {
      TranslateMessage(&message);
      DispatchMessageW(&message);
    }
    MsgWaitForMultipleObjects(0, nullptr, FALSE, 50, QS_ALLINPUT);
  }
  if (!complete || FAILED(asynchronous) || !controller) {
    std::cerr << "Controller creation failed: " << std::hex << asynchronous;
    return 6;
  }
  controller->Close();
  controller.Reset();
  environment.Reset();
  DestroyWindow(window);
  CoUninitialize();
  std::cout << "Source-only loader discovery/environment/controller passed" << std::endl;
  return 0;
}
