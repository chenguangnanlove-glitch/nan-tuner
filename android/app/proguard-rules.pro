# 当前未启用代码混淆（minifyEnabled false）。
# 若将来开启混淆，保留 WebView 的 JS 接口方法。
-keepclassmembers class com.shixin.tuner.MainActivity$AppBridge {
    @android.webkit.JavascriptInterface <methods>;
}
