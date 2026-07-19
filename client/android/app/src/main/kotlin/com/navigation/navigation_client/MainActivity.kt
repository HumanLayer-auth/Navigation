package com.navigation.navigation_client

import io.flutter.embedding.android.FlutterActivity
import io.flutter.embedding.engine.FlutterEngine

class MainActivity : FlutterActivity() {
    private var pdrBridge: PdrMotionBridge? = null

    override fun configureFlutterEngine(flutterEngine: FlutterEngine) {
        super.configureFlutterEngine(flutterEngine)
        pdrBridge = PdrMotionBridge(this, flutterEngine.dartExecutor.binaryMessenger)
    }
}
