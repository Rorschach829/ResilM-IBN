from mininet.net import Mininet
from mininet.node import RemoteController
from mininet.cli import CLI
from mininet.log import setLogLevel

def test_network():
    setLogLevel('info')

    net = Mininet(controller=RemoteController)

    # 添加远程控制器，IP和端口根据你的环境调整
    c0 = net.addController('c0', controller=RemoteController, ip='127.0.0.1', port=6633)

    # 添加主机和交换机
    h1 = net.addHost('h1')
    h2 = net.addHost('h2')
    s1 = net.addSwitch('s1')

    # 链接主机和交换机
    net.addLink(h1, s1)
    net.addLink(h2, s1)

    net.start()

    print("\n*** 测试所有主机之间的连通性 ***")
    net.pingAll()

    print("\n*** 进入Mininet命令行界面，可以执行命令 ***")
    CLI(net)

    net.stop()

if __name__ == '__main__':
    test_network()
