"""Spawn a cluster and setup the networking, don't do anything else. Try to allocate sm110p nodes. The difference between this and cluster-select-hardware is this profile contains the latest OS images."""

# Import the Portal object.
import geni.portal as portal
# Import the ProtoGENI library.
import geni.rspec.pg as pg
# Import the Emulab specific extensions.
import geni.rspec.emulab as emulab

# Pick your image.
imageList = [('urn:publicid:IDN+emulab.net+image+emulab-ops//UBUNTU20-64-STD', 'UBUNTU 20.04'),
             ('urn:publicid:IDN+emulab.net+image+emulab-ops//UBUNTU22-64-STD', 'UBUNTU 22.04')] 

# Create a portal object,
pc = portal.Context()

pc.defineParameter("slaveCount", "Number of slave nodes",
                   portal.ParameterType.INTEGER, 1)
pc.defineParameter("osImage", "Select Image",
                   portal.ParameterType.IMAGE,
                   imageList[0], imageList,
                   longDescription="Supported operating systems are Ubuntu and CentOS.") 
pc.defineParameter("publicIPSlaves", "Request public IP addresses for the slaves or not",
                   portal.ParameterType.BOOLEAN, True)
pc.defineParameter("secondNIC", "Have two experimental NICs that need to setup",
                   portal.ParameterType.BOOLEAN, False)

params = pc.bindParameters()


def create_request(request, role, ip, worker_num=None):
    if role == 'm':
        name = 'master'
    elif role == 's':
        name = 'worker{}'.format(worker_num)
    req = request.RawPC(name)
    if role == 'm':
        req.routable_control_ip = True
        req.hardware_type = 'sm110p'
    elif role == 's':
        req.routable_control_ip = params.publicIPSlaves
        req.hardware_type = 'sm110p'
    req.disk_image = params.osImage
    req.addService(pg.Execute(
        'bash',
        "sudo bash /local/repository/bootstrap.sh '{}' 2>&1 | sudo tee -a /local/logs/setup.log".format(
            role)))
    if params.secondNIC:
        iface = []
        iface.append(req.addInterface('eth1', pg.IPv4Address(ip, '255.255.255.0')))
        iface.append(req.addInterface('eth2', pg.IPv4Address('10.10.2.'+ip.split('.')[-1], '255.255.255.0')))
    else:
        iface = req.addInterface(
          'eth1', pg.IPv4Address(ip, '255.255.255.0'))
    return iface


# Create a Request object to start building the RSpec.
request = pc.makeRequestRSpec()

# Link link-0
link_0 = request.LAN('link-0')
link_0.Site('undefined')
if params.secondNIC:
    link_1 = request.LAN('link-1')
    link_1.Site('undefined')

# Master Node
iface = create_request(request, 'm', '10.10.1.1')
if params.secondNIC:
    link_0.addInterface(iface[0])
    link_1.addInterface(iface[1])
else:
    link_0.addInterface(iface)

# Slave Nodes
for i in range(params.slaveCount):
    iface = create_request(
        request, 's', '10.10.1.{}'.format(i + 2), worker_num=i)
    if params.secondNIC:
        link_0.addInterface(iface[0])
        link_1.addInterface(iface[1])
    else:
        link_0.addInterface(iface)


# Print the generated rspec
pc.printRequestRSpec(request)
