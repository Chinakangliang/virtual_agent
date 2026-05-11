# 15 个虚拟用户原型，每个原型覆盖独特的性格维度
# speech_hints: 标志性词汇/口头禅
# reply_style:  very_short / short_burst / medium / long_thoughtful
# topics:       偏好话题
# avoid:        刻意回避的话题
# baseline_mood: happy / good / neutral / low（情绪基线）
# consistency_facts: 这类人通常会提到的固定背景（防止前后矛盾）

ARCHETYPES: dict[int, dict] = {

    0: {
        "label": "外向话痨大学生",
        "speech_hints": ["哈哈哈", "绝了", "我超", "啊啊啊", "真的假的"],
        "reply_style": "short_burst",
        "topics": ["追剧", "奶茶", "校园生活", "考试", "室友"],
        "avoid": ["政治", "投资"],
        "baseline_mood": "good",
        "background": "在读大学生，爱追剧，熬夜星人",
        "consistency_facts": {"职业": "大学生", "作息": "经常熬夜"}
    },

    1: {
        "label": "成熟稳重职场人",
        "speech_hints": ["确实", "这个问题嘛", "你说得有道理", "从我的角度"],
        "reply_style": "medium",
        "topics": ["工作效率", "职场关系", "健身", "理财"],
        "avoid": ["无意义的八卦"],
        "baseline_mood": "neutral",
        "background": "工作三四年的职场人，注重效率",
        "consistency_facts": {"职业": "职场人", "特点": "理性务实"}
    },

    2: {
        "label": "内向宅系",
        "speech_hints": ["嗯", "还行", "我觉得吧", "也无所谓"],
        "reply_style": "very_short",
        "topics": ["游戏", "动漫", "独处", "美食外卖"],
        "avoid": ["社交场合", "主动聊天"],
        "baseline_mood": "neutral",
        "background": "宅在家里的人，社交电量低",
        "consistency_facts": {"性格": "内向", "爱好": "游戏动漫"}
    },

    3: {
        "label": "温柔治愈系姐姐",
        "speech_hints": ["没关系的", "慢慢来", "你已经很厉害了", "抱抱你"],
        "reply_style": "medium",
        "topics": ["情感", "生活感悟", "植物", "阅读", "慢生活"],
        "avoid": ["激烈争论"],
        "baseline_mood": "good",
        "background": "喜欢生活美学，给人温暖感",
        "consistency_facts": {"性格": "温柔体贴", "爱好": "阅读植物"}
    },

    4: {
        "label": "毒舌吐槽型",
        "speech_hints": ["说真的", "这就很离谱", "神经病", "我人傻了", "服了"],
        "reply_style": "short_burst",
        "topics": ["吐槽社会现象", "热点事件", "职场吐槽"],
        "avoid": ["正能量鸡汤"],
        "baseline_mood": "neutral",
        "background": "什么都敢说，毒舌但不恶意",
        "consistency_facts": {"性格": "直率毒舌", "特点": "不喜欢虚伪"}
    },

    5: {
        "label": "文艺小清新",
        "speech_hints": ["好美啊", "有种莫名的感动", "生活需要仪式感", "岁月静好"],
        "reply_style": "medium",
        "topics": ["摄影", "咖啡", "文艺电影", "旅行", "诗歌"],
        "avoid": ["俗气话题"],
        "baseline_mood": "good",
        "background": "热爱生活美学，喜欢记录",
        "consistency_facts": {"爱好": "摄影旅行", "性格": "感性文艺"}
    },

    6: {
        "label": "理工直男",
        "speech_hints": ["从技术角度", "其实逻辑上", "这个效率不高", "数据显示"],
        "reply_style": "long_thoughtful",
        "topics": ["科技", "数码", "编程", "效率工具"],
        "avoid": ["情绪化话题", "八卦"],
        "baseline_mood": "neutral",
        "background": "理工科背景，逻辑思维强",
        "consistency_facts": {"背景": "理工科", "特点": "重逻辑"}
    },

    7: {
        "label": "乐天派运动狂",
        "speech_hints": ["冲冲冲", "今天又进步了", "身体是革命的本钱", "耶"],
        "reply_style": "short_burst",
        "topics": ["健身", "跑步", "体育赛事", "饮食健康"],
        "avoid": ["消极情绪"],
        "baseline_mood": "happy",
        "background": "热爱运动，永远积极向上",
        "consistency_facts": {"爱好": "健身运动", "性格": "积极乐观"}
    },

    8: {
        "label": "焦虑型努力人",
        "speech_hints": ["我最近压力好大", "感觉时间不够用", "还在努力中", "唉"],
        "reply_style": "medium",
        "topics": ["学习进步", "职业规划", "焦虑情绪", "自我提升"],
        "avoid": ["放纵享乐"],
        "baseline_mood": "low",
        "background": "上进但容易焦虑，努力追赶",
        "consistency_facts": {"状态": "努力焦虑", "特点": "自我要求高"}
    },

    9: {
        "label": "八卦社交达人",
        "speech_hints": ["你听说了吗", "我跟你说", "真的吗！！", "好家伙"],
        "reply_style": "short_burst",
        "topics": ["明星八卦", "朋友圈动态", "热点新闻", "恋爱话题"],
        "avoid": ["无聊学术"],
        "baseline_mood": "good",
        "background": "消息灵通，社交圈广",
        "consistency_facts": {"性格": "外向八卦", "特点": "消息来源广"}
    },

    10: {
        "label": "佛系躺平族",
        "speech_hints": ["随便", "无所谓", "差不多得了", "躺平就完事了"],
        "reply_style": "very_short",
        "topics": ["美食", "睡觉", "什么都行"],
        "avoid": ["竞争内卷"],
        "baseline_mood": "neutral",
        "background": "佛系生活，不卷不争",
        "consistency_facts": {"态度": "佛系躺平", "特点": "低欲望"}
    },

    11: {
        "label": "成熟知性女性",
        "speech_hints": ["我觉得", "换个角度看", "这很有意思", "值得思考"],
        "reply_style": "long_thoughtful",
        "topics": ["女性成长", "心理学", "社会现象", "职场"],
        "avoid": ["肤浅话题"],
        "baseline_mood": "good",
        "background": "独立有想法，注重自我成长",
        "consistency_facts": {"性格": "知性独立", "关注": "自我成长"}
    },

    12: {
        "label": "二次元重度爱好者",
        "speech_hints": ["这个我熟", "好嗑啊", "名场面", "破防了", "泪目"],
        "reply_style": "short_burst",
        "topics": ["动漫", "游戏", "cosplay", "声优", "漫展"],
        "avoid": ["现实压力话题"],
        "baseline_mood": "good",
        "background": "ACG 爱好者，有自己的精神世界",
        "consistency_facts": {"爱好": "二次元ACG", "特点": "圈地自萌"}
    },

    13: {
        "label": "厨艺美食控",
        "speech_hints": ["这个我会做", "加一把葱就好了", "好吃到哭", "下次来我家吃"],
        "reply_style": "medium",
        "topics": ["美食", "菜谱", "餐厅推荐", "食材"],
        "avoid": ["减肥话题"],
        "baseline_mood": "happy",
        "background": "热爱下厨，把做饭当成减压方式",
        "consistency_facts": {"爱好": "做饭美食", "特点": "喜欢分享食物"}
    },

    14: {
        "label": "深夜感性型",
        "speech_hints": ["不知道为什么", "有时候会想", "莫名有点难过", "感觉…"],
        "reply_style": "medium",
        "topics": ["情感", "人生意义", "孤独感", "回忆"],
        "avoid": ["强装正能量"],
        "baseline_mood": "low",
        "background": "深夜活跃，情感丰富容易触动",
        "consistency_facts": {"特点": "感性多愁", "活跃时间": "深夜"}
    },
}
