#!/usr/bin/python
from __future__ import (absolute_import, division, print_function)
__metaclass__ = type
from pyVim.connect import SmartConnect, Disconnect
from pyVmomi import vim
import ssl
import json
import urllib

from ansible.module_utils.basic import AnsibleModule


class GetInfo():
    def __init__(self) -> None:
        self.vcenter_port = 443
        self.datastore_list = []

    def connect_vcenter(self,vcenters):
        context = ssl.SSLContext(ssl.PROTOCOL_TLSv1_2)
        context.verify_mode = ssl.CERT_NONE
        try: 
            self.si = SmartConnect(
                host=vcenters["vcenter_host"],
                user=vcenters["vcenter_user"],
                pwd=vcenters["vcenter_password"],
                port=self.vcenter_port,
                sslContext=context
            )
            self.content = self.si.RetrieveContent()
            return self.content
        except Exception as e :
            print("vCenter connection error: ", e)
            return False
              
    def get_all_objects(self,content, vimtype):
        obj = {}
        container = content.viewManager.CreateContainerView(content.rootFolder, vimtype, True)
        for managed_object_ref in container.view:
            obj.update({managed_object_ref: managed_object_ref.name})
        return obj  
      
    def decode_data(self,data):
        if isinstance(data, list):
            return [self.decode_data(item) for item in data]
        elif isinstance(data, dict):
            return {key: self.decode_data(value) for key, value in data.items()}
        elif isinstance(data, str):
            return urllib.parse.unquote(data)
        else:
            return data

    def datastore_data_parse(self,summary,vcenter_host):
        update_data_template = {
            "Datastore": summary.name,
            "vcenter_name": vcenter_host,
            "Capacity": (f"{summary.capacity / 1024 / 1024 / 1024} GB"),
            "Free Space": (f"{summary.freeSpace / 1024 / 1024 / 1024} GB"),
            "Type": summary.type
        }
        self.datastore_list.append(update_data_template)

    def disconnet_vcenter(self):
        Disconnect(self.si)

get_info = GetInfo()

def ds_list(vcenters_name):
    vcenters = vcenters_name
    for vcenters_index in vcenters:
        content = get_info.connect_vcenter(vcenters_index)
        datacenters = content.rootFolder.childEntity
        for datacenter in datacenters:
            datastores = datacenter.datastore
            for datastore in datastores:
                summary = datastore.summary
                get_info.datastore_data_parse(summary,vcenters_index["vcenter_host"])
        decoded_veriler = get_info.decode_data(get_info.datastore_list)
    return decoded_veriler

def main():
    module_args = dict(
        vcenters_name=dict(type='list', required=True)
    )    
    module = AnsibleModule(
        argument_spec=module_args,
        supports_check_mode=True
    )
    params = module.params
    vcenters_name = params['vcenters_name']
    try:
        data = ds_list(vcenters_name)
        get_info.disconnet_vcenter()
        module.exit_json(changed=False, data=data)
    except Exception as e:
        module.fail_json(msg=str(e))

if __name__ == '__main__':
    main()
