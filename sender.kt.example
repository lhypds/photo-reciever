
class Sender : AppCompatActivity(), SensorEventListener {
    private var imageCapture: ImageCapture? = null

    private lateinit var outputDirectory: File
    private lateinit var cameraExecutor: ExecutorService

    private lateinit var binding: ActivityMainBinding

    private val preferences by lazy { PrefUtils(this) }
    private lateinit var selectedImageFile: File

    var targetBluetoothDevice: String? = null

    // Bluetooth
    private var bluetoothService: BluetoothService? = null
    private lateinit var outStringBuffer: StringBuffer
    private lateinit var inStringBuffer: StringBuffer
    private lateinit var connectedDeviceName: String
    var bluetoothStatus: Int = BluetoothService.STATE_NONE
    var isBluetoothEnabled = false

    // Dialog
    lateinit var progressDialog: MaterialDialog

    // Keep alive
    private var keepAliveHandler = Handler(Looper.getMainLooper())
    private var keepAliveRunnable: Runnable? = null
    private var keepAliveHasResponse = false

    // Retry connect
    private var retryConnectHandler = Handler(Looper.getMainLooper())
    private var retryConnectRunnable: Runnable? = null

    private lateinit var locationCallback: LocationCallback
    private var currentLocation : Location? = null
    private var fusedLocationClient: FusedLocationProviderClient? = null

    private var dialog: Dialog? = null

    companion object {
        private const val REQUEST_CODE_PERMISSIONS = 10

        private val REQUIRED_PERMISSIONS = arrayOf(
            Manifest.permission.CAMERA,
            Manifest.permission.WRITE_EXTERNAL_STORAGE,
            Manifest.permission.READ_EXTERNAL_STORAGE,
            Manifest.permission.BLUETOOTH,
            Manifest.permission.BLUETOOTH_ADMIN
        )

        private val ALL_PERMISSIONS = arrayOf(
            Manifest.permission.CAMERA,
            Manifest.permission.WRITE_EXTERNAL_STORAGE,
            Manifest.permission.READ_EXTERNAL_STORAGE,
            Manifest.permission.BLUETOOTH,
            Manifest.permission.BLUETOOTH_ADMIN,
            Manifest.permission.ACCESS_COARSE_LOCATION,
            Manifest.permission.ACCESS_FINE_LOCATION
        )
    }

    // Bluetooth Functions

    // Check bluetooth
    // 1. Check hardware enabled
    // 2. Check target existing
    fun checkBluetooth(): Boolean {
        return checkBluetoothHardwareEnabled() && checkTargetDeviceExisting()
    }

    // Check bluetooth hardware
    fun checkBluetoothHardwareEnabled(): Boolean {
        val bluetoothAdapter = BluetoothAdapter.getDefaultAdapter()
        if (bluetoothAdapter == null || !bluetoothAdapter.isEnabled) {
            return false
        }
        return true
    }

    // Check target device existing in paired device list
    fun checkTargetDeviceExisting(): Boolean {
        if (preferences.targetBluetoothDevice.equals(Constants.INITIAL_TARGET_BLUETOOTH_DEVICE)) return true
        BluetoothAdapter.getDefaultAdapter() ?: return false

        // Get a set of currently paired devices
        val devices: MutableList<MyBluetoothDevice> = ArrayList()
        val pairedDevices = BluetoothAdapter.getDefaultAdapter().bondedDevices
        pairedDevices?.forEach {
            devices.add(MyBluetoothDevice(it))
        }

        // Check paired device list contains the target device
        pairedDevices?.forEach {
            if (preferences.targetBluetoothDevice?.contains(it.address)!!) {
                return true
            }
        }
        return false
    }

    private fun connect(address: String?) {
        // Get local Bluetooth adapter
        val mBluetoothAdapter = BluetoothAdapter.getDefaultAdapter()

        // If the adapter is null, then Bluetooth is not supported
        if (mBluetoothAdapter == null) {
            Timber.e("Bluetooth is not available")
            return
        }

        // Initialize the BluetoothChatService to perform bluetooth connections
        bluetoothService = BluetoothService(this, bluetoothServiceHandler)

        // Initialize the buffer for outgoing messages
        outStringBuffer = StringBuffer("")

        // Initialize the buffer for incoming messages
        inStringBuffer = StringBuffer("")

        // Get the BluetoothDevice object
        val device = mBluetoothAdapter.getRemoteDevice(address)

        // Attempt to connect to the device
        bluetoothService!!.connect(device, 4, true)
    }

    private fun connect() {
        // Connect, delay 1 sec to wait receiver restart
        Handler(Looper.getMainLooper()).postDelayed({
            if (targetBluetoothDevice != null && targetBluetoothDevice != "") {
                val address = targetBluetoothDevice?.split("\n")?.get(1)
                connect(address)
            }
        }, 2000)
    }

    fun disconnect() {
        if (bluetoothService == null) return

        // Send END reset receiver
        // Check that we're actually connected before trying anything
        if (bluetoothService!!.state != BluetoothService.STATE_CONNECTED) {
            Timber.e("Cannot send message: device is not connected")
            return
        }
        val bytes = "FIN".toByteArray()
        bluetoothService!!.write(bytes)

        // Reset out string buffer to zero and clear the edit text field
        outStringBuffer.setLength(0)

        bluetoothStatus = BluetoothState.STATE_NONE
        if (bluetoothService != null) {
            bluetoothService!!.stop()
        }
    }

    fun reconnect() {
        if (!checkBluetoothHardwareEnabled()) {
            DialogUtils.showToast(this, getString(R.string.turn_on_bluetooth))
            return
        }

        if (!checkTargetDeviceExisting()) {
            DialogUtils.showToast(this, getString(R.string.target_device_not_paired))
            return
        }

        disableBluetooth()
        enableBluetooth()
    }

    // Send a file
    fun send(file: File) {
        if (bluetoothService == null) return

        // Check that we're actually connected before trying anything
        if (bluetoothService!!.state != BluetoothService.STATE_CONNECTED) {
            Timber.e("Cannot send message: device is not connected")
            return
        }

        val bytes = File(file.absolutePath).readBytes()
        bluetoothService!!.write(bytes)

        // Reset out string buffer to zero and clear the edit text field
        outStringBuffer.setLength(0)
    }

    // Send a message
    fun send(message: String) {
        if (bluetoothService == null) return

        // Check that we're actually connected before trying anything
        if (bluetoothService!!.state != BluetoothService.STATE_CONNECTED) {
            Timber.e("Cannot send message: device is not connected")
            return
        }

        // Check that there's actually something to send
        if (message.isNotEmpty()) {
            // Get the message bytes and tell the BluetoothChatService to write
            val bytes = message.toByteArray()

            bluetoothService!!.write(bytes)

            // Reset out string buffer to zero and clear the edit text field
            outStringBuffer.setLength(0)
        }
    }

    // For receiving data
    private fun receive(data: String) {
        if (data == "ACK") {
            keepAliveHasResponse = true
            EventBus.getDefault().post(ServerAcknowledgedEvent())
        } else {
            // For other text, show as toast
            DialogUtils.showToast(this, data)
        }
    }

    private val bluetoothServiceHandler: Handler = @SuppressLint("HandlerLeak")
    object : Handler() {
        override fun handleMessage(msg: Message) {
            if (!isBluetoothEnabled) {
                disconnect()
                disableKeepAlive()
                disableRetryConnect()
                return
            }

            when (msg.what) {
                // Bluetooth status
                Constants.MESSAGE_STATE_CHANGE -> when (msg.arg1) {
                    BluetoothService.STATE_CONNECTED -> {
                        EventBus.getDefault()
                            .post(BluetoothStatusChangedEvent(BluetoothState.STATE_CONNECTED))

                        bluetoothStatus = BluetoothState.STATE_CONNECTED
                        Timber.d("Bluetooth status: Connected")

                        // Start keep alive
                        keepAlive()

                        // Stop retry
                        disableRetryConnect()
                    }

                    BluetoothService.STATE_CONNECTING -> {
                        EventBus.getDefault()
                            .post(BluetoothStatusChangedEvent(BluetoothState.STATE_CONNECTING))

                        bluetoothStatus = BluetoothState.STATE_CONNECTING
                        Timber.d("Bluetooth status: Connecting")

                        // Stop keep alive
                        disableKeepAlive()

                        // Stop retry
                        disableRetryConnect()
                    }

                    BluetoothService.STATE_LISTEN -> {
                        EventBus.getDefault()
                            .post(BluetoothStatusChangedEvent(BluetoothState.STATE_LISTEN))

                        bluetoothStatus = BluetoothState.STATE_LISTEN
                        Timber.d("Bluetooth status: Listen")

                        // Stop keep alive
                        disableKeepAlive()

                        // Start retry
                        retryConnect()
                    }

                    BluetoothService.STATE_NONE -> {
                        EventBus.getDefault()
                            .post(BluetoothStatusChangedEvent(BluetoothState.STATE_NONE))

                        bluetoothStatus = BluetoothState.STATE_NONE
                        Timber.d("Bluetooth status: None")

                        // Stop keep alive
                        disableKeepAlive()

                        // Start retry
                        retryConnect()
                    }
                }

                // Message write
                Constants.MESSAGE_WRITE -> {
                    val writeBuf = msg.obj as ByteArray

                    // construct a string from the buffer
                    val writeMessage = String(writeBuf)
                }

                // Message read
                Constants.MESSAGE_READ -> {
                    val readBuf = msg.obj as ByteArray

                    // construct a string from the valid bytes in the buffer
                    val readData = String(readBuf, 0, msg.arg1)

                    // message received
                    receive(readData)
                }

                // Message device name
                Constants.MESSAGE_DEVICE_NAME -> {
                    // save the connected device's name
                    connectedDeviceName = msg.data.getString("Device Name").toString()
                    Timber.d("Connected to $connectedDeviceName")
                }

                // Message toast
                Constants.MESSAGE_TOAST -> {
                    Timber.d(msg.data.getString("Toast")!!)
                }
            }
        }
    }

    fun retryConnect() {
        disableRetryConnect()
        if (isBluetoothEnabled) {
            retryConnectHandler.postDelayed(Runnable {
                DialogUtils.showToast(this, getString(R.string.retrying_connect))
                reconnect()
                retryConnect()
            }.also { retryConnectRunnable = it }, 10000)
        }
    }

    fun disableRetryConnect() {
        retryConnectHandler.removeCallbacksAndMessages(null)
        retryConnectRunnable?.let {
            retryConnectHandler.removeCallbacksAndMessages(it)
        }
    }

    fun keepAlive() {
        disableKeepAlive() // Clean
        if (isBluetoothEnabled) {
            keepAliveHasResponse = false // Reset to false
            send("IMA")

            keepAliveHandler.postDelayed(Runnable {
                if (keepAliveHasResponse) {
                    // Continue next keep alive message
                    keepAlive()
                } else {
                    DialogUtils.showToast(this, getString(R.string.receiver_has_no_response))
                    retryConnect()
                    EventBus.getDefault().post(BluetoothStatusChangedEvent(-1))
                }
            }.also { keepAliveRunnable = it }, 5000)
        }
    }

    fun disableKeepAlive() {
        keepAliveHandler.removeCallbacksAndMessages(null)
        keepAliveRunnable?.let {
            keepAliveHandler.removeCallbacksAndMessages(it)
        }
    }

    fun enableBluetooth() {
        Log.d("Bluetooth", "Enable bluetooth")
        isBluetoothEnabled = true
        connect()
    }

    fun disableBluetooth() {
        Log.d("Bluetooth", "Disable bluetooth")
        disableKeepAlive()
        disableRetryConnect()
        isBluetoothEnabled = false
        disconnect()
    }
}