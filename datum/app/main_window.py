import json
import re
from PyQt5.QtWidgets import *
from PyQt5.QtCore import Qt

#科创比赛ipc_socket 通信库引入
from ipc_socket.tcp_socket_client import HNNKTcpSocketClient
#自定义标题栏控件
from app.titile_bar import CustomTitleBar

#主窗口类
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        #科创client_socket实例初始化
        self.client_socket = HNNKTcpSocketClient()
        #绑定连接信号
        self.client_socket.server_connected.connect(self.on_server_connected)
        #绑定断开连接信号
        self.client_socket.server_disconnected.connect(self.on_server_disconnected)
        #绑定接收科创平台消息的信号
        self.client_socket.recv_from_server.connect(self.on_server_data)

        #相关属性
        self.connect_status = False #服务器是否连接
        self.layout_type = 0 #平台是默认布局模式还是分屏布局模式  0:默认布局  1:分屏布局

        #初始化ui
        self.init_ui()

        #居中显示
        self.show_window_center()

    #在屏幕中央居中显示
    def show_window_center(self):
        self.resize(1220, 490)
        screen = QDesktopWidget().screenGeometry()
        x = (screen.size().width() - self.geometry().width()) // 2
        y = (screen.size().height() - self.geometry().height()) // 2
        self.setGeometry(x, y, self.geometry().width(), self.geometry().height())
        self.show()

    # ui初始化
    def init_ui(self):
        # 设置无边框窗体，并居中显示
        self.setWindowFlags(Qt.FramelessWindowHint)
        self.setStyleSheet("background-color: white;")

        # 主内容布局：包含标题栏 + 内容区
        central_widget = QWidget(self)
        vbox = QVBoxLayout(central_widget)
        vbox.setSpacing(0)
        vbox.setContentsMargins(0, 0, 0, 0)

        # 标题栏区域
        self.title_bar = CustomTitleBar(self)
        vbox.addWidget(self.title_bar)

        # 客户区域
        client_widget = QWidget()
        vbox.addWidget(client_widget)

        '''
        客户区域自定义
        '''
        #连接区域
        connect_widget = QWidget()
        connect_widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        connect_hbox = QHBoxLayout()
        connect_hbox.setContentsMargins(40, 0, 40, 0)
        connect_hbox.setSpacing(20)

        #ip地址区域
        server_ip_widget = QWidget()
        server_ip_vbox = QVBoxLayout()
        server_ip_vbox.setSpacing(14)
        server_ip_vbox.setContentsMargins(0, 0, 0, 0)

        server_ip_label = QLabel('服务器地址')
        server_ip_label.setFixedHeight(16)
        server_ip_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        server_ip_label.setStyleSheet("""
               QLabel {
                   font-family: "SourceHanSansCN";
                   font-weight: 400;
                   font-size: 16px;
                   color: #9EA0A5;
                   line-height: 24px;
               }
           """)
        self.server_ip_lineedit = QLineEdit("127.0.0.1")
        self.server_ip_lineedit.setStyleSheet("""
            QLineEdit {
                background-color: #FFFFFF;
                border: 1px solid #ECF1F6;
                border-radius: 4px;
                padding-left: 10px;
                font-family: SourceHanSansCN, SourceHanSansCN;
                font-weight: 400;
                font-size: 18px;
                color: #3E3F42;
            }
        """)
        self.server_ip_lineedit.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        server_ip_vbox.addWidget(server_ip_label)
        server_ip_vbox.addWidget(self.server_ip_lineedit)
        server_ip_widget.setLayout(server_ip_vbox)

        #port区域
        server_port_widget = QWidget()
        server_port_vbox = QVBoxLayout()
        server_port_vbox.setSpacing(14)
        server_port_vbox.setContentsMargins(0, 0, 0, 0)

        server_port_label = QLabel('端口')
        server_port_label.setFixedHeight(16)
        server_port_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        server_port_label.setStyleSheet("""
                             QLabel {
                                 font-family: "SourceHanSansCN";
                                 font-weight: 400;
                                 font-size: 16px;
                                 color: #9EA0A5;
                                 line-height: 24px;
                             }
                         """)
        self.server_port_lineedit = QLineEdit("8000")
        self.server_port_lineedit.setStyleSheet("""
                   QLineEdit {
                       background-color: #FFFFFF;
                       border: 1px solid #ECF1F6;
                       border-radius: 4px;
                       padding-left: 10px;
                       font-family: SourceHanSansCN, SourceHanSansCN;
                       font-weight: 400;
                       font-size: 18px;
                       color: #3E3F42;
                   }
               """)

        self.server_port_lineedit.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        server_port_vbox.addWidget(server_port_label)
        server_port_vbox.addWidget(self.server_port_lineedit)
        server_port_widget.setLayout(server_port_vbox)

        #连接按钮区域
        server_btn_widget = QWidget()
        server_btn_vbox = QVBoxLayout()
        server_btn_vbox.setContentsMargins(0, 30, 0, 0)
        server_btn_hbox = QHBoxLayout()
        server_btn_hbox.setSpacing(10)
        server_btn_hbox.setContentsMargins(0, 0, 0, 0)

        self.connect_button = QPushButton("连接")
        self.connect_button.setStyleSheet("""
        QPushButton:enabled {
            font-family: SourceHanSansCN, SourceHanSansCN;
            font-weight: 400;
            font-size: 18px;
            color: #3E3F42;
        }
        QPushButton:disabled {
            font-family: SourceHanSansCN, SourceHanSansCN;
            font-weight: 400;
            font-size: 18px;
            color: rgba(62,63,66,0.4);
        }
        QPushButton{
            background: rgba(192,200,211,0.1);
            border-radius: 4px;
            border: 2px solid rgba(192,200,211,0.2);
        }
        """)
        self.connect_button.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.connect_button.clicked.connect(self.connect_server)

        self.disconnect_button = QPushButton("断开")
        self.disconnect_button.setEnabled(False)
        self.disconnect_button.setStyleSheet("""
        QPushButton:enabled {
            font-family: SourceHanSansCN, SourceHanSansCN;
            font-weight: 400;
            font-size: 18px;
            color: #3E3F42;
        }
        QPushButton:disabled {
            font-family: SourceHanSansCN, SourceHanSansCN;
            font-weight: 400;
            font-size: 18px;
            color: rgba(62,63,66,0.4);
        }
        QPushButton{
            background: rgba(192,200,211,0.1);
            border-radius: 4px;
            border: 2px solid rgba(192,200,211,0.2);
        }
        """)
        self.disconnect_button.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.disconnect_button.clicked.connect(self.disconnect_server)

        self.connect_status_label = QLabel('状态: 未连接')
        self.connect_status_label.setFixedHeight(16)
        self.connect_status_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.connect_status_label.setStyleSheet("""
            QLabel {
                font-family: "SourceHanSansCN";
                font-weight: 400;
                font-size: 16px;
                color: #9EA0A5;
                line-height: 24px;
            }
        """)
        self.connect_status_label.setAlignment(Qt.AlignCenter)

        server_btn_hbox.addWidget(self.connect_button, 1)
        server_btn_hbox.addWidget(self.disconnect_button, 1)
        server_btn_hbox.addWidget(self.connect_status_label, 1)

        server_btn_vbox.addLayout(server_btn_hbox)
        server_btn_widget.setLayout(server_btn_vbox)

        connect_hbox.addWidget(server_ip_widget, 1)
        connect_hbox.addWidget(server_port_widget, 1)
        connect_hbox.addWidget(server_btn_widget, 1)
        connect_widget.setLayout(connect_hbox)

        #自定义内容区域
        content_widget = QFrame()
        content_widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        content_widget.setObjectName("contentFrame")
        content_widget.setStyleSheet("""
            #contentFrame {
                border: 2px solid;
                border-color: #9EA0A5;
                border-radius: 4px;
            }
        """)
        content_layout = QVBoxLayout(content_widget)
        content_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        content_label = QLabel("自定义拓展区域")
        content_label.setStyleSheet("color: black; font-size: 16px;")
        content_layout.addWidget(content_label)

        client_box = QVBoxLayout()
        client_box.setContentsMargins(0, 0, 0, 0)
        client_box.setSpacing(24)

        #分配比例1:4的高度比例，保证默认布局和分屏布局尺寸自适应缩放
        client_box.addWidget(connect_widget, 1)
        client_box.addWidget(content_widget, 4)

        client_widget.setLayout(client_box)

        self.setCentralWidget(central_widget)

    #连接服务器
    def connect_server(self):
        host = self.server_ip_lineedit.text().strip()
        port_text = self.server_port_lineedit.text().strip()

        # 校验 IP 地址非空且格式正确
        ip_pattern = re.compile(r'^((25[0-5]|2[0-4]\d|1\d{2}|[1-9]?\d)(\.|$)){4}$')
        if not host:
            QMessageBox.warning(self, "输入错误", "IP 地址不能为空！")
            return
        if not ip_pattern.match(host):
            QMessageBox.warning(self, "输入错误", "请输入合法的 IP 地址！")
            return

        # 校验端口号非空且为整数（0-65535）
        if not port_text:
            QMessageBox.warning(self, "输入错误", "端口号不能为空！")
            return
        if not port_text.isdigit():
            QMessageBox.warning(self, "输入错误", "端口号必须是整数！")
            return

        port = int(port_text)
        if not (0 < port < 65536):
            QMessageBox.warning(self, "输入错误", "端口号必须在 1 到 65535 之间！")
            return

        self.client_socket.connect_server(host, port)

    #断开服务器
    def disconnect_server(self):
        self.client_socket.close_server()

    #当服务器连接上的时候
    def on_server_connected(self):
        print('on_server_connected')
        self.connect_status = True
        self.connect_button.setEnabled(False)
        self.disconnect_button.setEnabled(True)
        self.connect_status_label.setText("状态: 已连接")

    #当服务器断开的时候
    def on_server_disconnected(self):
        print('on_server_disconnected')
        self.connect_status = False
        self.connect_button.setEnabled(True)
        self.disconnect_button.setEnabled(False)
        self.connect_status_label.setText("状态: 已断开")

        # 如果是分屏布局，还需窗口分离
        if self.layout_type == 1:
            self.exit_server_window()
        else:
            self.show_window_center()

    # 收到科创平台数据后,解析json协议，协议详细信息参考doc/ipc通信协议
    def on_server_data(self, data):
        ipc_json_data = json.loads(data.data().decode('utf-8'))
        print('json_data', ipc_json_data)

        msg = ipc_json_data["msg"]
        if msg == 'ipc_algorithm_test':
            # 如果收到平台的算法在线模式的协议输出,会得到平台算法输出的指令
            result = ipc_json_data['result_args']['data']
            print(f'result= {result}')
        elif msg == 'ipc_user_info':
            #layout_type：0/1 默认布局/分屏布局
            self.layout_type = ipc_json_data['layout_type']
            '''
            1.如果是分屏布局，为了让案例和平台融合在一起的效果观感好看
            2.一旦连接上服务器收到ipc_user_info之后，需要将案例自己主窗口的标题栏隐藏, 
            3.而且必现向平台发送: ipc_user_info协议, 将自己的窗口主句柄告诉平台进程，如果不告诉，分屏效果将失败
            4.断开连接的时候，将案例自己主窗口的标题栏恢复可见
            '''
            if self.layout_type == 1:
                # 分屏模式自动隐藏标题栏
                self.title_bar.setVisible(False)
                self.ipc_user_info()

    #退出分屏模式
    def exit_server_window(self):
        self.title_bar.setVisible(True)
        self.show_window_center()

    # 告诉科创平台进程自己的主窗口句柄
    def ipc_user_info(self):
        if self.connect_status:
            data = {
                "msg": "ipc_user_info",
                "window": int(self.winId())
            }
            json_str = json.dumps(data)
            self.client_socket.send_to_server(json_str.encode('utf-8'))