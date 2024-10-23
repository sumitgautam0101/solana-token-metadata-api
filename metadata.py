from solders.pubkey import Pubkey
from solana.rpc.api import Client
import base58
import struct
import time

METADATA_PROGRAM_ID = Pubkey.from_string('metaqbxxUerdq28cj1RbAWkYQm3ybzjb6a8bt518x1s')

# Setup solana client, you can also pass your own RPC
solana_client = Client("https://api.mainnet-beta.solana.com/")

def get_nft_metadata_account(mint: str) -> Pubkey:
    """
    Derives the Program Derived Address (PDA) for a given NFT mint key on Solana.
    This PDA is used to locate the metadata account for an NFT on the Solana blockchain.
    
    Args:
        mint_key (str): The public key of the NFT's mint account, as a string.
        
    Returns:
        Pubkey: The derived Program Derived Address (PDA) associated with the NFT metadata.
    """
    
    #Convert the mint_key (string) into a Pubkey object
    mint_pubkey = Pubkey.from_string(mint)
    
    # Define the seeds for deriving the PDA
    # The seed includes: a string literal 'metadata', the metadata program ID, and the mint public key
    seeds = [
        b'metadata',                  # Constant string seed
        bytes(METADATA_PROGRAM_ID),   # Byte representation of the metadata program's public key
        bytes(mint_pubkey)            # Byte representation of the NFT mint's public key
    ]
    
    # Pubkey.find_program_address() returns a tuple (PDA, bump seed)
    pda, _bump_seed = Pubkey.find_program_address(seeds, METADATA_PROGRAM_ID)

    return pda

def unpack_metadata_account(data: bytes) -> dict:
    """
    Unpacks and parses the raw byte data of an NFT metadata account on the Solana blockchain.
    
    Args:
        data (bytes): Raw byte data containing NFT metadata.
    
    Returns:
        dict: A dictionary containing the unpacked metadata, including update authority, mint,
              name, symbol, URI, seller fee, creator information, and more.
    """
    
    # Ensure the first byte indicates a valid metadata account (4)
    assert(data[0] == 4)
    
    # Initialize byte index
    i = 1
    
    # Unpack the update authority (32 bytes)
    source_account = base58.b58encode(bytes(struct.unpack('<' + "B"*32, data[i:i+32])))
    i += 32
    
    # Unpack the mint account (32 bytes)
    mint_account = base58.b58encode(bytes(struct.unpack('<' + "B"*32, data[i:i+32])))
    i += 32
    
    # Unpack the length and name of the NFT (variable length)
    name_len = struct.unpack('<I', data[i:i+4])[0]
    i += 4
    name = struct.unpack('<' + "B"*name_len, data[i:i+name_len])
    i += name_len
    
    # Unpack the length and symbol of the NFT (variable length)
    symbol_len = struct.unpack('<I', data[i:i+4])[0]
    i += 4
    symbol = struct.unpack('<' + "B"*symbol_len, data[i:i+symbol_len])
    i += symbol_len
    
    # Unpack the length and URI of the NFT (variable length)
    uri_len = struct.unpack('<I', data[i:i+4])[0]
    i += 4
    uri = struct.unpack('<' + "B"*uri_len, data[i:i+uri_len])
    i += uri_len
    
    # Unpack the seller fee (2 bytes)
    fee = struct.unpack('<h', data[i:i+2])[0]
    i += 2
    
    # Check if creators are present (1 byte)
    has_creator = data[i]
    i += 1
    
    # Initialize creator-related lists
    creators = []
    verified = []
    share = []
    
    # If there are creators, unpack their data
    if has_creator:
        creator_len = struct.unpack('<I', data[i:i+4])[0]
        i += 4
        for _ in range(creator_len):
            creator = base58.b58encode(bytes(struct.unpack('<' + "B"*32, data[i:i+32])))
            creators.append(creator)
            i += 32
            
            # Unpack the verified status (1 byte per creator)
            verified.append(data[i])
            i += 1
            
            # Unpack the creator's share (1 byte per creator)
            share.append(data[i])
            i += 1
    
    # Unpack the primary sale happened flag (1 byte)
    primary_sale_happened = bool(data[i])
    i += 1
    
    # Unpack the mutability flag (1 byte)
    is_mutable = bool(data[i])
    
    # Structure the unpacked metadata into a dictionary
    metadata = {
        "update_authority": source_account,
        "mint": mint_account,
        "data": {
            "name": bytes(name).decode("utf-8").strip("\x00"),   # Remove null characters
            "symbol": bytes(symbol).decode("utf-8").strip("\x00"), # Remove null characters
            "uri": bytes(uri).decode("utf-8").strip("\x00"),      # Remove null characters
            "seller_fee_basis_points": fee,  # Seller's fee in basis points (1/100 of a percent)
            "creators": creators,
            "verified": verified,
            "share": share,
        },
        "primary_sale_happened": primary_sale_happened,
        "is_mutable": is_mutable,
    }
    
    return metadata

def get_metadata(mint: str, solana_client: Client) -> dict:
    """
    Fetches and returns the metadata for a given NFT mint key on the Solana blockchain.
    
    Args:
        mint_key (str): The public key of the NFT's mint account.
        
    Returns:
        dict: A dictionary containing the NFT metadata such as name, symbol, URI, and creator information.
    """
    
    #Derive the Program Derived Address (PDA) for the NFT metadata
    nft_pda = get_nft_metadata_account(mint)

    # In case of an error try to fetch data 2 more times
    for _ in range(3):

        try:
        
            #Fetch account information for the derived PDA
            acc_info = solana_client.get_account_info(nft_pda)
            
            # Check if the account data is available
            if not acc_info or not acc_info.value:
                raise ValueError(f"No account information found for PDA: {nft_pda}")
            
            break
            
        except:
            time.sleep(5)
        
    # Extract raw data from the account
    data = acc_info.value.data
    
    # Unpack the metadata from the raw data
    token_metadata = unpack_metadata_account(data)
    
    # Return the decoded metadata
    return token_metadata


"""Example"""
metadata = get_metadata("7ZxT5cMtWog3dvg2jMsLhgNY8iA8ewdt8tDkvVYVGG1G", solana_client)

print(metadata)