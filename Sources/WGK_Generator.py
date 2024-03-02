
import qrcode
import subprocess
from routeros_ssh_connector import MikrotikDevice


# This program will generate configs for wireguard.
# you will need to install qrcode and pillow in python
# and you need to install wireguard, so that you can call wg from your terminal

################### Router Connector ##################
router = MikrotikDevice()
from routeros_ssh_connector import MikrotikDevice
Router_IP = input("Please enter the Mikrotik IP address : ")
Mik_User_Name =  input("Please enter the Mikrotik username : ")
Mik_Password =  input("Please enter the Mikrotik Password : ")
Mik_SSH_Port =  input("Please enter Mikrotik SSH port (Default is 22) : ")

if Mik_SSH_Port=="":
    Mik_SSH_Port = 22

router = MikrotikDevice()
router.connect(f"{Router_IP}", f"{Mik_User_Name}", f"{Mik_Password}", Mik_SSH_Port)


################### Modify your settings here ##################
# Get interface name
interface_name = input("Please Enter the name of interface : ")

# Get the listen port from user
listen_port = input("Please Enter Listen Port : ")


# Set the endpoint
endpoint_IP = input("Please Enter Endpoint : ")
endpoint = endpoint_IP+":"+listen_port

#Get thenumber of needed clients

clients = int(input("Please enter the number of needed clients : "))


# Set preshared_key to True to create preshared keys or False if not needed
preshared_key = False

# Set your DNS Server like "1.1.1.1" or empty string "" if not needed
# maybe you want to use a dns server on your server e.g. 192.168.1.1
# maybe you want to use a dns server on your server e.g. 192.168.1.1
dns = input("Please enter Dns : ")

# Set your vpn tunnel network (example is for 10.99.99.0/24)

IPnet = input("Please enter the tunnel nework according to this format XXX.XXX.XXX.XXX : ")
IPnet_parts = IPnet.split('.')


# Set allowed IPs (this should be the network of the server you want to access)
# If you want to route all traffic over the VPN then set tunnel_0_0_0_0 = True, the network in allowed ips will then be ignored
#allowed_ips = "192.168.1.0/24"
tunnel_0_0_0_0 = True

# If you need iptables rules then set iptables= "eth0" (replace eth0 with the name of your network card) or iptables = "" if no rules needed
iptables = ""

################### Do not edit below this line ##################

wg_priv_keys = []
wg_pub_keys = []
wg_psk = []


def main():
    # Gen-Keys
    for _ in range(clients+1):
        (privkey, pubkey, psk) = generate_wireguard_keys()
        #psk = generate_wireguard_psk()
        wg_priv_keys.append(privkey)
        wg_pub_keys.append(pubkey)
        wg_psk.append(psk)




    ################# Server-Config ##################
    
    server_config = "[Interface]\n" \
        f"Address = {IPnet_parts[0]}.{IPnet_parts[1]}.{IPnet_parts[2]}.{int(IPnet_parts[3])+1}/24\n" \
        f"ListenPort = {listen_port}\n" \
        f"PrivateKey = {wg_priv_keys[0]}\n"
    if iptables:
        server_config += f"PostUp = iptables -A FORWARD -i %i -j ACCEPT; iptables -t nat -A POSTROUTING -o {iptables} -j MASQUERADE\n" \
            f"PostDown = iptables -D FORWARD -i %i -j ACCEPT; iptables -t nat -D POSTROUTING -o {iptables} -j MASQUERADE\n"

    
    print("*"*10 + " Server-Conf " + "*"*10)
    print(server_config)
    make_qr_code_png(server_config, f"server.png")

    with open(f"server.conf", "wt") as f:
        f.write(server_config)

        

    ################# Client-Configs ##################
    client_configs = []
    for i in range(1, clients+1):
        
        client_config = f"[Interface]\n" \
            f"PrivateKey = {wg_priv_keys[i]}\n"\
            f"Address = {IPnet_parts[0]}.{IPnet_parts[1]}.{IPnet_parts[2]}.{int(IPnet_parts[3])+1+i}/24\n" 
            
        if dns:
            client_config += f"DNS = {dns}\n\n"

        

        client_config += f"[Peer]\n" \
            f"PublicKey = {wg_pub_keys[0]}\n" 
           

        
        client_config += f"AllowedIPs = 0.0.0.0/0\n"

        client_config += f"Endpoint = {endpoint}\n"
        client_configs.append(client_config)

        print("*"*10 + f" Client-Conf {i} " + "*"*10)
        print(client_config)
        make_qr_code_png(client_config, f"client_{i}.png")
        with open(f"client_{i}.conf", "wt") as f:
            f.write(client_config)

    #print("*"*10 + " Debugging " + "*"*10 )
    #print("*"*10 + " Priv-Keys " + "*"*10 )
    # print(wg_priv_keys)
    #print("*"*10 + " Pub-Keys " + "*"*10 )
    # print(wg_pub_keys)

    ################# Mikrotik Command Builder  ##################

    Mik_Commands = []
    for j in range(1,clients+1):
        Mik_Command = f"interface wireguard peers add allowed-address={IPnet_parts[0]}.{IPnet_parts[1]}.{IPnet_parts[2]}.{int(IPnet_parts[3])+j+1}/32 "\
                      f"interface={interface_name} public-key=\"{wg_pub_keys[j]}\""                 
        router.send_command(Mik_Command)
        Mik_Commands.append(Mik_Command)


    with open(r"Mik_Commands.txt","w") as f:
        f.write("\n".join(str(command) for command in Mik_Commands))

    del router
        

     ################# Public Keys File Builder  ##################
    Client_Pub_Keys = []
    for k in range(1,clients+1):
        Client_Pub_Key = f"Clinet{k} PublicKey = {wg_pub_keys[k]}"
        Client_Pub_Keys.append(Client_Pub_Key)

    with open("Client_Pub_Keys.txt","w") as f:
        f.write("\n".join(str(cpk) for cpk in Client_Pub_Keys))



def generate_wireguard_keys():
    privkey = subprocess.check_output(
        "wg genkey", shell=True).decode("utf-8").strip()
    pubkey = subprocess.check_output(
        f"echo '{privkey}' | wg pubkey", shell=True).decode("utf-8").strip()
    psk = subprocess.check_output(
        "wg genkey", shell=True).decode("utf-8").strip()
    return (privkey, pubkey, psk)


def make_qr_code_png(text, filename):
    img = qrcode.make(text)
    img.save(f"{filename}")


if __name__ == "__main__":
    main()
