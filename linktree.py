from dataclasses import dataclass
from typing import List, Union, Optional
import sys
import asyncio
import aiohttp
from bs4 import BeautifulSoup
import json

@dataclass
class Link:
    url : Optional[str]
    
@dataclass
class LinktreeUser:
    username : str
    url : Optional[str]
    avartar_image : Optional[str]
    id : int
    tier : str
    isActive : bool
    description : Optional[str]
    createdAt: int
    updatedAt: int
    links : List[Link]

class Linktree(object):
    async def _fetch(self, url : str,
                     method : str = "GET", 
                     headers : dict = {}, 
                     data : dict = {}) -> tuple[aiohttp.ClientSession, aiohttp.ClientSession]:
        
        session = aiohttp.ClientSession(headers= headers)
        resp = await session.request(method = method ,url = url, json = data)
        return session, resp
                    
    async def getSource(self, url : str):
        session, resp = await self._fetch(url)
        content = await resp.text()
        await session.close()
        return content
            
    async def getUserInfoJSON(self, source = None,  url : Optional[str] = None, username : Optional[str] = None):            
        if url is None and username:
            url = f"https://linktr.ee/{username}"

        if source is None and url:
            source = await self.getSource(url)

        soup = BeautifulSoup(source, 'html.parser')
        attributes = {"id":"__NEXT_DATA__"}
        user_info = soup.find('script', attrs=attributes)
        user_data = json.loads(user_info.contents[0])["props"]["pageProps"]
        return user_data

    async def uncensorLinks(self, account_id : int, link_ids : Union[List[int], int]):
        if isinstance(link_ids, int):
            link_ids = [link_ids]
        
        headers = {"origin": "https://linktr.ee",
                   "referer": "https://linktr.ee",
                   "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.77 Safari/537.36"}
        
        data = {"accountId": account_id, 
                   "validationInput": {"acceptedSensitiveContent": link_ids},
                 "requestSource": {"referrer":None}}
        
        url = "https://linktr.ee/api/profiles/validation/gates"
        session, resp = await self._fetch(method = "POST", url = url, headers = headers, data= data)
        
        json_resp = await resp.json()
        await session.close()
        
        _links = json_resp["links"]
        
        links = []
        for _link in _links:
            url = _link["url"]
            link = Link(url = url)
            links.append(link)
        return links
    
    async def getUserLinks(self, username : Optional[str] = None, data : Optional[dict] = None):
        if data is None and username:
            data = await self.getUserInfoJSON(username= username)
            
        user_id = data["account"]["id"]
        _links = data["links"]
    
        links = []
        censored_links_ids = []
        
        for _link in _links:
            id = int(_link["id"])
            url = _link["url"]
            locked = _link["locked"]

            link = Link(url = url)
            if _link["type"] == "COMMERCE_PAY":
                continue
            
            if url is None and locked is True:
                censored_links_ids.append(id)
                continue
            links.append(link)

        uncensored_links = await self.uncensorLinks(account_id= user_id, 
                                                    link_ids= censored_links_ids)
        links.extend(uncensored_links)
        
        return links

    async def getLinktreeUserInfo(self, url : Optional[str] = None, username : Optional[str] = None)-> LinktreeUser:
        if url is None and username is None:
            print("Please pass linktree username or url.")
            return

        JSON_INFO = await self.getUserInfoJSON(url = url, username= username)
        account = JSON_INFO["account"]
        username = account["username"]
        avatar_image = account["profilePictureUrl"]
        url = f"https://linktr.ee/{username}" if url is None else url 
        id = account["id"]
        tier  = account["tier"]
        isActive = account["isActive"]
        createdAt = account["createdAt"]
        updatedAt = account["updatedAt"]
        description = account["description"]

        links = await self.getUserLinks(data= JSON_INFO)
        
        return LinktreeUser(username = username,
                            url = url,
                            avartar_image= avatar_image,
                            id = id,
                            tier = tier,
                            isActive = isActive,
                            createdAt = createdAt,
                            updatedAt = updatedAt,
                            description = description,
                            links = links)

    
async def main():
    # url = "https://linktr.ee/Pale_but_peachy"
    
    if len(sys.argv) < 2:
        print("Username or url is needed!")
        sys.exit(1)

    input = sys.argv[1]
    if "linktr.ee" in input:
        username, url = None, input
    else:
        username, url = input, None

    linktree = Linktree()
    user_info = await linktree.getLinktreeUserInfo(username = username, 
                                                    url= url)
    print(f"username : {user_info.username}")
    print(f"avatar image: {user_info.avartar_image}")
    print(f"tier : {user_info.tier}")
    print(f"isActive : {user_info.isActive}")
    print(f"descripition : {user_info.description}")
    print(f"createdAt : {user_info.createdAt}")
    print(f"updatedAt : {user_info.updatedAt}")

    print("\nLinks:")
    for link in user_info.links:
        print(link.url)
        

if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())

