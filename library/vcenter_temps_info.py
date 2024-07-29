#!/usr/bin/python
from __future__ import (absolute_import, division, print_function)
__metaclass__ = type
from pyVim.connect import SmartConnect, Disconnect
from pyVmomi import vim
import ssl
import urllib

from ansible.module_utils.basic import AnsibleModule

class GetInfo():
    def __init__(self) -> None:
        self.vcenter_port = 443
        self.temp_list = []

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
            print("vCenter baglanti problemi: ", e)
            return False
        
    def get_all_objects(self,content):
        obj_view = content.viewManager.CreateContainerView(content.rootFolder, [vim.VirtualMachine], True)
        vms = obj_view.view
        obj_view.Destroy()
        return vms
    
    def decode_data(self,data):
        if isinstance(data, list):
            return [self.decode_data(item) for item in data]
        elif isinstance(data, dict):
            return {key: self.decode_data(value) for key, value in data.items()}
        elif isinstance(data, str):
            return urllib.parse.unquote(data)
        else:
            return data
    
    def temp_data_parse(self,vm,vcenter_host):
        summary = vm.summary
        config = vm.config
        update_data_template = {
            "Template Name": summary.config.name,
            "Guest:": summary.config.guestFullName,
            "vcenter_name": vcenter_host,
            "Instance UUID": summary.config.instanceUuid,
            "Path to VM": summary.config.vmPathName,
            "Number of vCPUs": config.hardware.numCPU,
            "Memory (MB)": config.hardware.memoryMB,
            "Storage Comitted (KB)": (f"{summary.storage.committed / 1024 / 1024 } KB"),
            "Storage Uncomitted (KB)": (f"{summary.storage.uncommitted / 1024 / 1024 } KB"),
            "Storage Unshared (KB)": (f"{summary.storage.unshared / 1024 / 1024 } KB"),
            "Power State":summary.runtime.powerState,
            "IP Address": summary.guest.ipAddress,
            "Host:": summary.runtime.host.name
        }
        self.temp_list.append(update_data_template)       

    def disconnet_vcenter(self):
        Disconnect(self.si)

get_info = GetInfo()


def temp_list(vcenters_name):
    vcenters = vcenters_name
    for vcenters_index in vcenters:
        content = get_info.connect_vcenter(vcenters_index)
        vms = get_info.get_all_objects(content)
        templates = [vm for vm in vms if vm.config.template]
        for template in templates:
            get_info.temp_data_parse(template,vcenters_index["vcenter_host"])
        decoded_veriler = get_info.decode_data(get_info.temp_list)
    
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
        data = temp_list(vcenters_name)
        get_info.disconnet_vcenter()
        module.exit_json(changed=False, data=data)
    except Exception as e:
        module.fail_json(msg=str(e))

if __name__ == '__main__':
    main()

