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
        self.dvs_list = []

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
    
    def dvs_create_data(self,dc_name,vcenter_host,dvs_name,pg_name,vlan,isTrunk):
        if not isTrunk:
            update_data_template = {
                "Datacenter": dc_name,
                "vcenter_name": vcenter_host,
                "Distributed Virtual Switch": dvs_name,
                "Portgroup": pg_name,
                "VLAN": vlan
            }
            self.dvs_list.append(update_data_template)
        else: 
            update_data_template = {
                "Datacenter": dc_name,
                "vcenter_name": vcenter_host,
                "Distributed Virtual Switch": dvs_name,
                "Portgroup": pg_name,
                "VLAN Trunk Range": vlan
            }
            self.dvs_list.append(update_data_template)

    def disconnet_vcenter(self):
        Disconnect(self.si)

get_info = GetInfo()

def dvs_list(vcenters_name):
    vcenters = vcenters_name
    for vcenters_index in vcenters:
        content = get_info.connect_vcenter(vcenters_index)
        datacenters = get_info.get_all_objects(content, [vim.Datacenter])
        for dc in datacenters:
            dc_name = dc.name
            dvswitches = get_info.get_all_objects(content, [vim.DistributedVirtualSwitch])
            for dvs in dvswitches:
                dvs_name = dvs.name
                portgroups = dvs.portgroup
                for pg in portgroups:
                    pg_name = pg.name
                    vlan = pg.config.defaultPortConfig.vlan
                    if isinstance(vlan, vim.dvs.VmwareDistributedVirtualSwitch.TrunkVlanSpec):
                        for range in vlan.vlanId:
                            vlan_trunk_range= (f"{range.start} - {range.end}")
                        get_info.dvs_create_data(dc_name,vcenters_index["vcenter_host"],dvs_name,pg_name,vlan_trunk_range,1)
                    else:
                        vlan_id = pg.config.defaultPortConfig.vlan.vlanId
                        get_info.dvs_create_data(dc_name,vcenters_index["vcenter_host"],dvs_name,pg_name,vlan_id,0)
        decoded_veriler = get_info.decode_data(get_info.dvs_list)
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
        data = dvs_list(vcenters_name)
        get_info.disconnet_vcenter()
        module.exit_json(changed=False, data=data)
    except Exception as e:
        module.fail_json(msg=str(e))

if __name__ == '__main__':
    main()
