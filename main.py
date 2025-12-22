from astrbot.api.event import filter, AstrMessageEvent, MessageEventResult
from astrbot.api.star import Context, Star, register,StarTools
from astrbot.api import logger,AstrBotConfig
import astrbot.api.message_components as Comp
from astrbot.core.platform.sources.aiocqhttp.aiocqhttp_message_event import AiocqhttpMessageEvent
import os,aiohttp,json,asyncio


@register("skinCodeAdmin", "Guailoudou", "一个简单的 Hello World 插件", "1.0.0")
class skinCodeAdmin(Star):
    def __init__(self, context: Context,config: AstrBotConfig):
        super().__init__(context)
        self.config = config
        self.data_dir = StarTools.get_data_dir()
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.userdata_file = self.data_dir / r"skinCode_user.json"
        self.groupdata_file = self.data_dir / r"skinCode_group.json"
        logger.info(f"初始化用户数据文件{self.userdata_file}and 群组数据文件{self.groupdata_file}成功")
        self.userdata = {}
        self.groupdata = {}
        
    async def initialize(self):
        """可选择实现异步的插件初始化方法，当实例化该插件类之后会自动调用该方法。"""
        await self.get_userdata_file()
        await self.get_groupdata_file()
        logger.info("skincodeadmin插件初始化完成")
    @filter.permission_type(filter.PermissionType.ADMIN)
    @filter.command("code_init")
    async def init(self, event: AstrMessageEvent):
        await self.get_userdata_file()
        await self.get_groupdata_file()
        yield event.plain_result("已重新读取数据文件")

    # 注册指令的装饰器。指令名为 helloworld。注册成功后，发送 `/helloworld` 就会触发这个指令，并回复 `你好, {user_name}!`
    @filter.permission_type(filter.PermissionType.ADMIN)
    @filter.command("getallcodes")
    async def cmd_getallcodes(self, event: AstrMessageEvent):
        """获取服务端的所有的邀请码""" # 这是 handler 的描述，将会被解析方便用户了解插件内容。建议填写。
        # user_name = event.get_sender_name()
        # message_str = event.message_str # 用户发的纯文本消息字符串
        # message_chain = event.get_messages() # 用户所发的消息的消息链 # from astrbot.api.message_components import *
        # logger.info(message_chain)
        free,used = await self.getallcodes()
        yield event.plain_result(f"剩余{len(free)} \n\n 已使用{len(used)}")
        # yield event.plain_result(f"Hello, {user_name}, 你发了 {message_str}!") # 发送一条纯文本消息

    @filter.event_message_type(filter.EventMessageType.PRIVATE_MESSAGE) # 私聊
    @filter.command("getmecode", alias={'获取邀请码'})
    async def cmd_getnewcode(self, event: AstrMessageEvent):
        """获取我的邀请码，限制私聊"""
        message_obj = event.message_obj
        qq = message_obj.sender.user_id
        logger.info(f"获取用户{qq}的等级")

        qqlevel = await self.getqqLevel(event,qq)
        if(qqlevel < 15):
            yield event.plain_result("你没有权限使用此功能,QQ等级过低")
            return
        if(qq not in self.userdata.keys()):
            yield event.plain_result(f"获取中，请稍后...")
            await self.new_user(qq)
        else:
            if(self.userdata[qq]["code"] != ""):
                yield event.plain_result(f"你已经获取过邀请码了，请勿重复获取，你的邀请码是：{self.userdata[qq]['code']}")
                return
        newcode = await self.getnewcode()
        self.userdata[qq]["code"] = newcode
        await self.save_userdata()
        yield event.plain_result(f"这是你的邀请码: {newcode}")
    

    @filter.permission_type(filter.PermissionType.ADMIN)
    @filter.command("pass")
    async def cmd_pass(self, event: AstrMessageEvent, qq: str):
        """通过用户白名单"""
        if qq not in self.userdata.keys():
            await self.new_user(qq)
        await self.setpass(qq,True)
        yield event.plain_result(f"已通过用户{qq}白名单")
    @filter.permission_type(filter.PermissionType.ADMIN)
    @filter.command("ban")
    async def cmd_ban(self, event: AstrMessageEvent, qq: str):
        """封禁用户"""
        if qq not in self.userdata.keys():
            await self.new_user(qq)
        await self.setpass(qq,False)
        await self.setban(qq,True)
        for gid in self.groupdata["user"]:
            from astrbot.core.platform.sources.aiocqhttp.aiocqhttp_message_event import AiocqhttpMessageEvent
            assert isinstance(event, AiocqhttpMessageEvent)
            payloads = {
                    "group_id": gid,
                    "user_id": qq,
                    "reject_add_request": False
                }  
            await event.bot.call_action("set_group_kick", **payloads)
            logger.info(f"提出用户{qq}成功在{gid}群中")
        yield event.plain_result(f"已封禁用户{qq}，并踢出相关群,他的皮肤站uid为{self.userdata[qq]['skin_uid']}")

    @filter.permission_type(filter.PermissionType.ADMIN)
    @filter.command("unban")
    async def cmd_unban(self, event: AstrMessageEvent, qq: str):
        """解封用户"""
        if qq not in self.userdata.keys():
            await self.new_user(qq)
        await self.setban(qq,False)
        yield event.plain_result(f"已解封用户{qq}")

    @filter.command("invite")
    async def cmd_invite(self, event: AstrMessageEvent, qq: str):
        """邀请用户"""
        message_obj = event.message_obj
        meqq = message_obj.sender.user_id
        if meqq not in self.userdata.keys():
            await self.new_user(meqq)
        if not self.userdata[meqq]["is_pass"]:
            yield event.plain_result("请你自己先通过白名单")
            return
        if qq not in self.userdata.keys():
            await self.new_user(qq)
        userdata = self.userdata[qq]
        if userdata["is_banned"]:
            yield event.plain_result("对方已被封禁，无法邀请")
            return
        if userdata["is_pass"] == True:
            yield event.plain_result(f"用户{qq}已经通过白名单，无需邀请")
            return
        else:
            userdata["is_pass"] = True
            userdata["superior"] = meqq
            self.userdata[meqq]["subordinates"].append(qq)
            self.save_userdata()
            yield event.plain_result(f"已成功邀请用户{qq}，请注意，你们现在绑定为了上下级关系，一个犯事，联合处罚")

    @filter.permission_type(filter.PermissionType.ADMIN)
    @filter.command("sugroup")
    async def cmd_setusergroup(self, event: AstrMessageEvent):
        """设置群为用户群，即限制白名单自动审批群，需要管理员权限"""
        raw_message = event.message_obj.raw_message
        group_id = raw_message.get("group_id", "")
        self.groupdata["user"].append(group_id)
        await self.save_groupdata()
        yield event.plain_result(f"已设置群{group_id}为用户群")

    @filter.command("smgroup")
    async def cmd_setmsggroup(self, event: AstrMessageEvent):
        """设置群为消息群"""
        self.groupdata["msg"].append(event.unified_msg_origin)
        await self.save_groupdata()
        yield event.plain_result(f"已设置会话{event.unified_msg_origin}为通知群")

    @filter.command("rmgroup")
    async def cmd_rmmsggroup(self, event: AstrMessageEvent):
        """取消群为消息群"""
        # self.groupdata["msg"].append(event.unified_msg_origin)
        self.groupdata["msg"].remove(event.unified_msg_origin)
        await self.save_groupdata()
        yield event.plain_result(f"已取消会话{event.unified_msg_origin}为通知群")

    @filter.permission_type(filter.PermissionType.ADMIN)
    @filter.command("send")
    async def cmd_sendmsg(self, event: AstrMessageEvent):
        """发送消息到消息群"""
        await self.sendmsg(event)
        event.stop_event()
    @filter.permission_type(filter.PermissionType.ADMIN)
    @filter.command("query")
    async def cmd_query(self, event: AstrMessageEvent,qq:str):
        """查询用户信息"""
        msg = f"{qq}的相关用户信息:"
        if(qq not in self.userdata.keys()):
            yield event.plain_result(msg+"无信息")
            return
        msg = await self.query(event,qq)
        yield event.plain_result(msg)
        associated = await self.get_associated(qq)
        yield event.plain_result(f"所有相关联的QQ:{associated}")

    @filter.command("setname")
    async def cmd_setname(self, event: AstrMessageEvent, name: str):
        """设置用户昵称"""
        message_obj = event.message_obj
        qq = message_obj.sender.user_id
        if (qq not in self.userdata.keys()):
            await self.new_user(qq)
        self.userdata[qq]["name"] = name
        await self.save_userdata()
        yield event.plain_result(f"已设置昵称为{name}")
    
    @filter.permission_type(filter.PermissionType.ADMIN)
    @filter.command("sync")
    async def sync(self, event: AstrMessageEvent):
        """同步皮肤站用户信息"""
        _,used = await self.getallcodes()
        
        for userdata in self.userdata.values():
            if userdata["code"]!="" and userdata["skin_uid"] == "":
                for codeused in reversed(used):
                    if codeused["code"]==userdata["code"]:
                        userdata["skin_uid"]=codeused["used_by"]
                        logger.info(f"同步用户{userdata['id']}的皮肤站uid{codeused['used_by']}信息成功")
                        break
        yield event.plain_result(f"已成功同步所有皮肤站账号信息")

    @filter.permission_type(filter.PermissionType.ADMIN)
    @filter.command("allban")
    async def cmd_allban(self, event: AstrMessageEvent, qq:int):
        """封禁所有相关用户"""
        await self.cmd_ban(event, qq)
        associated = await self.get_associated(qq)
        for qq in associated:
            await self.cmd_ban(event, qq)
        event.stop_event()
     
    async def query(self, event: AstrMessageEvent,qq: str):
        """查询用户信息"""
        msg = f"{qq}的相关用户信息:"
        userdata = self.userdata[qq]
        msg += f"\n用户id:{userdata['id']}"
        msg += f"\n用户昵称:{userdata['name']}"
        msg += f"\n皮肤站邀请码:{userdata['code']}"
        msg += f"\n皮肤站uid:{userdata['skin_uid']}"
        msg += f"\n是否通过审核:{userdata['is_pass']}"
        msg += f"\n是否被ban:{userdata['is_banned']}"
        msg += f"\n邀请者:{userdata['superior']}"
        msg += f"\n邀请了："
        for ins in userdata['subordinates']:
            msg += f"{ins}，"
        return msg

    async def get_associated(self, qq: str):
        """获取所有关联的用户"""
        userdata = self.userdata[qq]
        data = []
        #寻找最上级
        if userdata['superior'] != "":
            superior = userdata['superior']
            while self.userdata[superior]['superior'] != "":
                superior = self.userdata[superior]['superior']
            data.append(superior)
        else:
            superior = qq
        #从最上级开始寻找所有下级，还有下级的下级，添加到data中、
        subdata = await self.getallsubordinate(superior)
        return data + subdata
       
    #递归寻找所有下级
    async def getallsubordinate(self, qq: str):
        """递归寻找所有下级"""
        data = []
        userdata = self.userdata.get(qq, {"subordinates": []})
        for subordinate in userdata["subordinates"]:
            data.append(subordinate)
            subdata = await self.getallsubordinate(subordinate)
            data.extend(subdata)  # 添加递归结果
        return data


    async def setpass(self, qq: str,ispass: bool):
        """设置用户白名单"""
        userdata = self.userdata[qq]
        userdata["is_pass"] = ispass
        await self.save_userdata()
    
    async def setban(self, qq: str,isban: bool):
        """设置用户黑名单"""
        userdata = self.userdata[qq]
        userdata["is_banned"] = isban
        await self.save_userdata()

    async def getnewcode(self):
        """获取新的邀请码"""
        free,_ = await self.getallcodes()
        for code in free:
            isfree = True
            for data in self.userdata.values():
                if data["code"] == code["code"]:
                    isfree = False
                    break
            if isfree:
                return code["code"]

    async def new_user(self, qq: str ):
        """创建新的用户信息"""
        userdata = self.userdata
        userdata[qq]={
            "id": qq,
            "name": "",
            "code": "",
            "skin_uid": "",
            "is_pass": False,
            "is_banned": False, 
            "superior": "", 
            "subordinates": []   
        }
        await self.save_userdata()
        logger.info(f"创建用户 {qq}")
    async def sendmsg(self,event: AstrMessageEvent):
        """发送消息给所有消息群"""
        
        groups = self.groupdata["msg"]
        message_obj = event.message_obj
        qq = message_obj.sender.user_id
        if (qq not in self.userdata.keys()):
            await self.new_user(qq)
        if(self.userdata[qq]["name"]!=""):
            user_name = self.userdata[qq]["name"]
        else:
            user_name = event.get_sender_name()
        # chain = [
        #     Comp.Plain(f"[消息推送]\n{event.message_str[5:]}\n-by {user_name}"),
        # ]
        # logger.info(f"{event.message_obj.raw_message}")
        # for group in groups:
        #     await self.context.send_message(group,event.chain_result(chain))
        # from astrbot.core.platform.sources.aiocqhttp.aiocqhttp_message_event import AiocqhttpMessageEvent
        assert isinstance(event, AiocqhttpMessageEvent)
        message = event.message_obj.raw_message.get("message")
        if message[0]["type"]=="text":
            message[0]["data"]["text"]=message[0]["data"]["text"][6:]
        upmsg = {"type": "text", "data": {"text": f"[转发信息]\n"}}
        endmsg = {"type": "text", "data": {"text": f"\n-by {user_name}"}}
        # message.insert(0, upmsg)
        message.append(endmsg)
        logger.info(message)
        # groups = ["aiocqhttp:GroupMessage:233491069"] #测试用
        for group in groups:
            if(group==event.unified_msg_origin):continue
            payloads = {
                            "group_id": group[23:],
                            "messages": [
                                            {
                                                "type": "node",
                                                "data": {
                                                    "user_id": qq,
                                                    "nickname": user_name,
                                                    "content": message
                                                    
                                                }
                                            }
                                        ],
                            "news": [
                                        {
                                            "text": f"{user_name}:[公告]"
                                        }
                                    ],
                            "prompt": "群发公告信息",
                            "summary": f"点我查看最新公告信息",
                            "source": "小游戏群bot群发活动公告信息"
                        }  
            logger.info(f"群{group[23:]}发送")
            try:
                # await event.bot.call_action("send_group_msg", **payloads)
                await event.bot.call_action("send_group_forward_msg", **payloads)
                logger.info(f"群{group[23:]}已发送")
            except Exception as e:
                logger.info(f"群{group[23:]}发送失败：{e}")
    async def save_userdata(self):
        """保存用户数据到文件"""
        with open(self.userdata_file, "w", encoding="utf-8") as f:
            json.dump(self.userdata, f)
    async def save_groupdata(self):
        """保存群数据到文件"""
        with open(self.groupdata_file, "w", encoding="utf-8") as f:
            json.dump(self.groupdata, f)
    async def get_userdata_file(self):
        """读取文件获取用户数据"""
        logger.info("正在读取用户数据文件")
        self.userdata = await self.get_file(self.userdata_file)
        logger.info(f"用户数据文件读取完毕")
        

    async def get_groupdata_file(self):
        """获取群数据文件"""
        logger.info(f"正在读取群数据文件")
        self.groupdata = await self.get_file(self.groupdata_file,{"user":[],"admin":[],"temp":[],"msg":[]})
        logger.info(f"群数据文件读取完毕")
    async def get_file(self, dir ,init={}):
        """获取文件"""
        if not os.path.exists(dir):
            with open(dir, "w", encoding="utf-8") as f:
                json.dump(init, f)
        with open(dir, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data
    async def getallcodes(self):
        try:
            url = self.config.api_url
            logger.info(f"开始请求{url}获取数据")
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as response:
                    if response.status == 200:
                        data = await response.json()
                        logger.info(f"获取数据成功")
                        return data["free"], data["used"]
                    else:
                        logger.error(f"请求失败: {response.status}")
                        return None
        except Exception as e:
            logger.error(f"请求失败: {e}")
            return None
 #群管理部分 参考https://github.com/qiqi55488/astrbot_plugin_appreview/blob/master/main.py
    @filter.event_message_type(filter.EventMessageType.ALL)
    async def handle_group_request(self, event: AstrMessageEvent):
        """处理群聊申请事件"""
        # 检查是否为请求事件
        if not hasattr(event, "message_obj") or not hasattr(event.message_obj, "raw_message"):
            return
            
        raw_message = event.message_obj.raw_message
        if not raw_message or not isinstance(raw_message, dict):
            return
        
        # 检查是否为群组请求事件
        if raw_message.get("post_type") != "request":
            return
        
        # 确保message_obj有session_id属性
        # self.set_session_id(event)
        
        # 处理加群请求
        if raw_message.get("request_type") == "group" and raw_message.get("sub_type") == "add":
            await self.process_group_join_request(event, raw_message)
    async def process_group_join_request(self, event: AstrMessageEvent, request_data):
        """处理加群请求"""
        flag = request_data.get("flag", "")
        user_id = request_data.get("user_id", "")
        user_id = str(user_id)
        comment = request_data.get("comment", "")
        group_id = request_data.get("group_id", "")
        
        logger.info(f"收到加群请求: 用户ID={user_id}, 群ID={group_id}, 验证信息={comment} ,请求标识={flag}")
        if (group_id not in self.groupdata["user"]):
            logger.info(f"群{group_id}未在配置文件中")
            return
        if (user_id not in self.userdata.keys()):
            await self.new_user(user_id)
        if self.userdata[user_id]["is_banned"]:
            await self.approve_request(event,flag,False,"你已被封禁，拒绝加入")
            logger.info(f"用户{user_id}已封禁，拒绝加入")
            return
        if(self.userdata[user_id]["is_pass"]):
            await self.approve_request(event,flag,True)
            logger.info(f"已通过加群请求: 用户ID={user_id}, 群ID={group_id}, 验证信息={comment} {self.userdata[user_id]['is_pass']}")
        else:
            await self.approve_request(event,flag,False,"你未拥有该群白名单")
            logger.info(f"已拒绝加群请求: 用户ID={user_id}, 群ID={group_id}, 验证信息={comment} {self.userdata[user_id]['is_pass']}")


    async def approve_request(self, event: AstrMessageEvent, flag, approve=True, reason=""):
        """同意或拒绝请求"""
        try:
            # 确保message_obj有session_id属性
            # self.set_session_id(event)
            
            # 检查是否为aiocqhttp平台
            if event.get_platform_name() == "aiocqhttp":
                # 使用NapCat API格式
                # from astrbot.core.platform.sources.aiocqhttp.aiocqhttp_message_event import AiocqhttpMessageEvent
                assert isinstance(event, AiocqhttpMessageEvent)
                client = event.bot  
                payloads = {
                    "flag": flag,
                    "approve": approve,
                    "reason": reason if reason else ""
                }         
                await client.call_action('set_group_add_request', **payloads)
                logger.info(f'已处理加群请求: {flag} {approve} {reason}')
                return True
           
            return False
        except Exception as e:
            logger.error(f"处理群聊申请失败: {e}")
            return False
    
    async def getqqLevel(self, event: AstrMessageEvent,qq):
        if event.get_platform_name() == "aiocqhttp":
                # 使用NapCat API格式
                # from astrbot.core.platform.sources.aiocqhttp.aiocqhttp_message_eve nt import AiocqhttpMessageEvent
                assert isinstance(event, AiocqhttpMessageEvent)
                client = event.bot  
                payloads = {
                    "user_id": qq
                }         
                ret = await client.call_action('get_stranger_info', **payloads)
                qqlevel = ret['qqLevel']
                logger.info(f'已成功获取qq等级:{qqlevel}')
                return qqlevel
    async def terminate(self):
        """可选择实现异步的插件销毁方法，当插件被卸载/停用时会调用。"""
