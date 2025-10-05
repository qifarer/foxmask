# debug_enums.py
import asyncio
import aiohttp
import json

async def debug_server_enums():
    """调试服务器实际的枚举值"""
    enum_queries = [
        "UploadTaskTypeGql",
        "UploadSourceTypeGql", 
        "UploadStrategyGql",
        "FileTypeGql"
    ]
    
    for enum_name in enum_queries:
        query = f"""
        query {{
            __type(name: "{enum_name}") {{
                name
                kind
                enumValues {{
                    name
                    description
                }}
            }}
        }}
        """
        
        async with aiohttp.ClientSession() as session:
            async with session.post(
                "http://localhost:8888/graphql",
                json={"query": query},
                headers={"Content-Type": "application/json"}
            ) as response:
                result = await response.json()
                print(f"\n🔍 {enum_name}:")
                if 'data' in result and '__type' in result['data']:
                    enum_type = result['data']['__type']
                    print(f"   Kind: {enum_type['kind']}")
                    for value in enum_type['enumValues']:
                        print(f"   - {value['name']}: {value.get('description', '')}")
                else:
                    print("   Error:", json.dumps(result.get('errors', 'Unknown error'), indent=2, ensure_ascii=False))

if __name__ == "__main__":
    asyncio.run(debug_server_enums())