import argparse

import anvil.server
import anvil.users


def validate_anvil_user(anvil_key, username, password):
    anvil.server.connect(anvil_key)

    try:
        # raises AuthenticationFailed error if incorrect
        user = anvil.users.login_with_email(
            username,
            password
        )
        return user
    except:
        return False
    
def link_user_node(anvil_key, username, password, node_name):
    user = validate_anvil_user(
        anvil_key=anvil_key,
        username=username,
        password=password
    )
    anvil.server.connect(anvil_key)
    anvil.server.call('link_user_node', node_name)
    return user

    
if __name__ == "__main__":
    
    parser = argparse.ArgumentParser()
    
    parser.add_argument(
        "--anvil_key",
        type=str,
        default="client_RIH6JESGB46H5H2C26QNTEPN-WCK6VK5MLEHD7BEC"
    )
    parser.add_argument(
        "--username",
        type=str,
        default="carlos.fernandez.musoles@gmail.com"
    )
    parser.add_argument(
        "--password",
        type=str,
        default="iekeopru"
    )
    args = parser.parse_args()
    
    
    link_user_node(args.anvil_key, args.username, args.password, "carlosfm-laptop")
    
