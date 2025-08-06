# backend/controller/ryu_topology_rest.py

from ryu.app.wsgi import ControllerBase, WSGIApplication, route
from ryu.topology.api import get_switch, get_link
from webob import Response
import json


class TopologyRestController(ControllerBase):
    def __init__(self, req, link, data, **config):
        super(TopologyRestController, self).__init__(req, link, data, **config)

    # ping   localhost:8081/v1.0/topology/links可以获取当前链路信息
    @route('topo_links', '/v1.0/topology/links', methods=['GET'])
    def get_links(self, req, **kwargs):
        link_list = get_link(None, None)
        body = []
        for link in link_list:
            src = {'dpid': link.src.dpid, 'port_no': link.src.port_no}
            dst = {'dpid': link.dst.dpid, 'port_no': link.dst.port_no}
            body.append({'src': src, 'dst': dst})
        return Response(content_type='application/json',
                        body=json.dumps(body).encode('utf-8'))
