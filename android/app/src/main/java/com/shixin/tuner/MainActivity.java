package com.shixin.tuner;

import android.Manifest;
import android.app.Activity;
import android.app.AlertDialog;
import android.content.Intent;
import android.content.pm.PackageManager;
import android.graphics.Color;
import android.net.Uri;
import android.os.Bundle;
import android.util.Log;
import android.util.TypedValue;
import android.view.Gravity;
import android.view.View;
import android.view.ViewGroup;
import android.view.WindowManager;
import android.webkit.JavascriptInterface;
import android.webkit.PermissionRequest;
import android.webkit.WebChromeClient;
import android.webkit.WebResourceRequest;
import android.webkit.WebResourceResponse;
import android.webkit.WebSettings;
import android.webkit.WebView;
import android.widget.FrameLayout;
import android.widget.ImageView;
import android.widget.LinearLayout;
import android.widget.TextView;
import android.widget.Toast;

import androidx.annotation.NonNull;
import androidx.webkit.WebResourceErrorCompat;
import androidx.webkit.WebViewAssetLoader;
import androidx.webkit.WebViewClientCompat;

import org.json.JSONObject;

import java.io.BufferedReader;
import java.io.InputStreamReader;
import java.net.HttpURLConnection;
import java.net.URL;
import java.nio.charset.StandardCharsets;

/**
 * 「始信音乐 · 调音器」Android 外壳。
 *
 * 设计要点：
 *  1. 启动直接打开安装包内置页（offline.html）。国内访问线上站经常要十余秒，
 *     先等远程页会黑屏；内置页走 WebViewAssetLoader，属于安全上下文，麦克风照常可用。
 *  2. 若之后导航到远程页且主框架加载失败，再回退到内置页并提示。
 *  3. 麦克风权限由本类接管，弹一次系统授权即可长期使用。
 *  4. 启动后异步检查 app-version.json，有新版 APK 则提示更新（跳系统浏览器下载）。
 */
public class MainActivity extends Activity {

    private static final String TAG = "ShixinTuner";
    private static final int REQ_MIC = 1001;

    /** 内置离线页（appassets 域名由 WebViewAssetLoader 提供，属于 HTTPS 安全上下文） */
    private static final String LOCAL_PAGE =
            "https://appassets.androidplatform.net/assets/offline.html";

    private static final String SITE_HOST = hostOf(BuildConfig.SITE_URL);

    private WebView webView;
    private WebViewAssetLoader assetLoader;
    private View splashView;
    private PermissionRequest pendingMicRequest;
    private boolean onLocalFallback = false;
    private boolean updateDialogShown = false;

    private static String hostOf(String url) {
        try {
            String h = new URL(url).getHost();
            return h == null ? "" : h.toLowerCase();
        } catch (Exception e) {
            return "";
        }
    }

    // ============================================================
    //  生命周期
    // ============================================================

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);

        // 调音过程中屏幕保持常亮（否则熄屏会中断麦克风采集）
        getWindow().addFlags(WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON);

        assetLoader = new WebViewAssetLoader.Builder()
                .addPathHandler("/assets/", new WebViewAssetLoader.AssetsPathHandler(this))
                .build();

        FrameLayout root = new FrameLayout(this);
        root.setBackgroundColor(Color.parseColor("#0e0c0a"));

        webView = new WebView(this);
        webView.setBackgroundColor(Color.parseColor("#0e0c0a"));
        root.addView(webView, new FrameLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT,
                ViewGroup.LayoutParams.MATCH_PARENT));
        attachSplash(root);

        setContentView(root);

        configureWebView();
        loadLocalPage(false);      // 本地优先；正常启动不弹「已切换到内置版本」
        checkForUpdate();          // 异步，失败不影响使用
    }

    @Override
    protected void onResume() {
        super.onResume();
        if (webView != null) webView.onResume();
    }

    @Override
    protected void onPause() {
        if (webView != null) webView.onPause();
        super.onPause();
    }

    @Override
    @SuppressWarnings("deprecation")
    public void onBackPressed() {
        if (webView != null && webView.canGoBack()) {
            webView.goBack();
        } else {
            super.onBackPressed();
        }
    }

    @Override
    protected void onDestroy() {
        if (webView != null) {
            webView.loadUrl("about:blank");
            webView.removeAllViews();
            webView.destroy();
            webView = null;
        }
        super.onDestroy();
    }

    // ============================================================
    //  WebView 配置
    // ============================================================

    private void configureWebView() {
        WebSettings s = webView.getSettings();
        s.setJavaScriptEnabled(true);
        s.setDomStorageEnabled(true);          // localStorage：保存用户的 A4 校准值等
        s.setDatabaseEnabled(true);
        s.setMediaPlaybackRequiresUserGesture(false);
        s.setCacheMode(WebSettings.LOAD_DEFAULT);
        s.setUseWideViewPort(true);
        s.setLoadWithOverviewMode(true);
        s.setSupportZoom(false);
        s.setBuiltInZoomControls(false);
        s.setDisplayZoomControls(false);
        s.setTextZoom(100);                    // 忽略系统字体缩放，避免界面被撑破
        s.setAllowFileAccess(false);
        s.setAllowContentAccess(false);
        s.setGeolocationEnabled(false);
        s.setMixedContentMode(WebSettings.MIXED_CONTENT_NEVER_ALLOW);

        webView.setOverScrollMode(WebView.OVER_SCROLL_NEVER);
        webView.setVerticalScrollBarEnabled(false);
        webView.setHorizontalScrollBarEnabled(false);
        webView.setLongClickable(false);

        // 供网页判断「当前运行在 App 里」，例如隐藏“下载 App”的提示
        webView.addJavascriptInterface(new AppBridge(), "ShixinApp");

        webView.setWebViewClient(new WebViewClientCompat() {

            @Override
            public WebResourceResponse shouldInterceptRequest(WebView view, WebResourceRequest request) {
                return assetLoader.shouldInterceptRequest(request.getUrl());
            }

            @Override
            public boolean shouldOverrideUrlLoading(WebView view, WebResourceRequest request) {
                Uri uri = request.getUrl();
                String scheme = uri.getScheme() == null ? "" : uri.getScheme().toLowerCase();
                String host = uri.getHost() == null ? "" : uri.getHost().toLowerCase();

                boolean isHttp = "http".equals(scheme) || "https".equals(scheme);
                if (isHttp && !host.isEmpty()
                        && (host.equals(SITE_HOST) || host.equals("appassets.androidplatform.net"))) {
                    // 主框架离开内置页去线上时，允许失败后再回退并提示
                    if (request.isForMainFrame() && host.equals(SITE_HOST)) {
                        onLocalFallback = false;
                    }
                    return false;                 // 自己的站点与内置页，留在 App 内导航
                }
                openExternally(uri);              // 其它链接（含 APK 下载）交给系统浏览器
                return true;
            }

            @Override
            public void onPageCommitVisible(@NonNull WebView view, @NonNull String url) {
                if (isAppContent(url)) hideSplash();
            }

            @Override
            public void onPageFinished(@NonNull WebView view, @NonNull String url) {
                if (isAppContent(url)) hideSplash();
            }

            @Override
            public void onReceivedError(@NonNull WebView view,
                                        @NonNull WebResourceRequest request,
                                        @NonNull WebResourceErrorCompat error) {
                if (!request.isForMainFrame()) return;
                if (!onLocalFallback) {
                    Log.w(TAG, "远程页面加载失败，回退到内置版本");
                    loadLocalPage();
                } else {
                    hideSplash();
                }
            }
        });

        webView.setWebChromeClient(new WebChromeClient() {
            @Override
            public void onPermissionRequest(final PermissionRequest request) {
                runOnUiThread(() -> handleWebPermission(request));
            }
        });

        // 网页里的下载链接也走系统浏览器
        webView.setDownloadListener((url, userAgent, contentDisposition, mimeType, contentLength) ->
                openExternally(Uri.parse(url)));
    }

    // ============================================================
    //  麦克风权限
    // ============================================================

    private void handleWebPermission(PermissionRequest request) {
        boolean wantsMic = false;
        for (String r : request.getResources()) {
            if (PermissionRequest.RESOURCE_AUDIO_CAPTURE.equals(r)) {
                wantsMic = true;
                break;
            }
        }
        if (!wantsMic) {
            request.deny();
            return;
        }

        if (checkSelfPermission(Manifest.permission.RECORD_AUDIO) == PackageManager.PERMISSION_GRANTED) {
            request.grant(new String[]{PermissionRequest.RESOURCE_AUDIO_CAPTURE});
        } else {
            pendingMicRequest = request;         // 等系统授权结果回来再决定
            requestPermissions(new String[]{Manifest.permission.RECORD_AUDIO}, REQ_MIC);
        }
    }

    @Override
    public void onRequestPermissionsResult(int requestCode, @NonNull String[] permissions,
                                           @NonNull int[] grantResults) {
        super.onRequestPermissionsResult(requestCode, permissions, grantResults);
        if (requestCode != REQ_MIC || pendingMicRequest == null) return;

        boolean granted = grantResults.length > 0
                && grantResults[0] == PackageManager.PERMISSION_GRANTED;

        if (granted) {
            pendingMicRequest.grant(new String[]{PermissionRequest.RESOURCE_AUDIO_CAPTURE});
        } else {
            pendingMicRequest.deny();
            Toast.makeText(this, R.string.mic_denied, Toast.LENGTH_LONG).show();
        }
        pendingMicRequest = null;
    }

    // ============================================================
    //  页面加载：启动即内置页；远程主框架失败时才回退并提示
    // ============================================================

    /** 远程页失败时的回退入口，会提示「已切换到内置版本」。 */
    private void loadLocalPage() {
        loadLocalPage(true);
    }

    /**
     * @param showOfflineNotice 正常启动传 false。只有「先开了远程页、再失败回退」才提示离线。
     */
    private void loadLocalPage(boolean showOfflineNotice) {
        if (onLocalFallback) return;
        onLocalFallback = true;
        webView.loadUrl(LOCAL_PAGE);
        if (showOfflineNotice) {
            Toast.makeText(this, R.string.offline_toast, Toast.LENGTH_SHORT).show();
        }
    }

    /** 盖在 WebView 上的启动层：深色底 + 图标 +「加载中」，页面真正显示后卸掉。 */
    private void attachSplash(FrameLayout root) {
        float density = getResources().getDisplayMetrics().density;

        LinearLayout box = new LinearLayout(this);
        box.setOrientation(LinearLayout.VERTICAL);
        box.setGravity(Gravity.CENTER);
        box.setBackgroundColor(getColor(R.color.app_bg));

        ImageView logo = new ImageView(this);
        logo.setImageResource(R.mipmap.ic_launcher);
        logo.setScaleType(ImageView.ScaleType.FIT_CENTER);
        logo.setContentDescription(getString(R.string.app_name));
        int size = Math.round(72 * density);
        box.addView(logo, new LinearLayout.LayoutParams(size, size));

        TextView label = new TextView(this);
        label.setText(R.string.splash_loading);
        label.setTextColor(getColor(R.color.app_accent));
        label.setTextSize(TypedValue.COMPLEX_UNIT_SP, 16);
        label.setGravity(Gravity.CENTER);
        LinearLayout.LayoutParams labelLp = new LinearLayout.LayoutParams(
                ViewGroup.LayoutParams.WRAP_CONTENT,
                ViewGroup.LayoutParams.WRAP_CONTENT);
        labelLp.topMargin = Math.round(16 * density);
        box.addView(label, labelLp);

        splashView = box;
        root.addView(splashView, new FrameLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT,
                ViewGroup.LayoutParams.MATCH_PARENT));
    }

    private void hideSplash() {
        if (splashView == null) return;
        View splash = splashView;
        splashView = null;
        ViewGroup parent = (ViewGroup) splash.getParent();
        if (parent != null) parent.removeView(splash);
    }

    /** about:blank 是 WebView 清空页面时的中间态，不能把它当成「内容已显示」。 */
    private static boolean isAppContent(String url) {
        return url != null && !url.isEmpty() && !"about:blank".equals(url);
    }

    /** 用系统浏览器 / 其它 App 打开外部链接 */
    private void openExternally(Uri uri) {
        try {
            Intent i = new Intent(Intent.ACTION_VIEW, uri);
            i.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK);
            startActivity(i);
        } catch (Exception e) {
            Toast.makeText(this, R.string.no_link_handler, Toast.LENGTH_SHORT).show();
        }
    }

    // ============================================================
    //  版本检查（读取站点根目录的 app-version.json）
    // ============================================================

    private void checkForUpdate() {
        Thread t = new Thread(() -> {
            HttpURLConnection conn = null;
            try {
                URL url = new URL(BuildConfig.SITE_URL + "/app-version.json?t="
                        + System.currentTimeMillis());
                conn = (HttpURLConnection) url.openConnection();
                conn.setConnectTimeout(6000);
                conn.setReadTimeout(6000);
                conn.setRequestProperty("Accept", "application/json");
                if (conn.getResponseCode() != HttpURLConnection.HTTP_OK) return;

                StringBuilder sb = new StringBuilder();
                try (BufferedReader rd = new BufferedReader(
                        new InputStreamReader(conn.getInputStream(), StandardCharsets.UTF_8))) {
                    String line;
                    while ((line = rd.readLine()) != null) sb.append(line);
                }

                JSONObject json = new JSONObject(sb.toString());
                int remoteCode = json.optInt("versionCode", BuildConfig.VERSION_CODE);
                if (remoteCode <= BuildConfig.VERSION_CODE) return;   // 已是最新

                String remoteName = json.optString("versionName", "");
                String notes = json.optString("notes", "");
                String apk = json.optString("apk", "/download/shixin-tuner.apk");
                String downloadUrl = apk.startsWith("http") ? apk : BuildConfig.SITE_URL + apk;

                runOnUiThread(() -> showUpdateDialog(remoteName, notes, downloadUrl));

            } catch (Exception e) {
                Log.w(TAG, "版本检查失败：" + e.getMessage());
            } finally {
                if (conn != null) conn.disconnect();
            }
        }, "shixin-version-check");
        t.setDaemon(true);
        t.start();
    }

    private void showUpdateDialog(String versionName, String notes, String downloadUrl) {
        if (isFinishing() || updateDialogShown) return;
        updateDialogShown = true;

        String msg = (notes == null || notes.trim().isEmpty())
                ? getString(R.string.update_default_note)
                : notes;
        String title = getString(R.string.update_title)
                + (versionName.isEmpty() ? "" : " " + versionName);

        new AlertDialog.Builder(this)
                .setTitle(title)
                .setMessage(msg)
                .setPositiveButton(R.string.update_now,
                        (d, w) -> openExternally(Uri.parse(downloadUrl)))
                .setNegativeButton(R.string.update_later, null)
                .show();
    }

    // ============================================================
    //  提供给网页的 JS 接口：window.ShixinApp
    // ============================================================

    public static class AppBridge {

        @JavascriptInterface
        public boolean isNativeApp() {
            return true;
        }

        @JavascriptInterface
        public String getVersionName() {
            return BuildConfig.VERSION_NAME;
        }

        @JavascriptInterface
        public int getVersionCode() {
            return BuildConfig.VERSION_CODE;
        }
    }
}
