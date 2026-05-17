(function () {
  'use strict';

  window.SCENE_CATEGORIES = {
    all: {label: '全部', icon: '🌐'},
    marketing: {label: '营销增长', icon: '📈'},
    business: {label: '商业决策', icon: '🏢'},
    career: {label: '职场发展', icon: '💼'},
    professional: {label: '专业服务', icon: '🔧'}
};
  window.SCENE_UI_CONFIG = {
    ecommerce: {title: '电商增长', icon: '🛍️', category: 'marketing', desc: '围绕商品与人群，输出可执行增长方案。', fields: [
        {key: 'product_info', label: '产品信息', type: 'textarea', rows: 3, full: true, required: true, placeholder: '例如：美妆新品，客单价189元，主打25-35岁女性'},
        {key: 'target_audience', label: '目标人群', type: 'textarea', rows: 2, placeholder: '例如：小红书+抖音为主，一二线城市'},
        {key: 'current_stage', label: '当前阶段', type: 'input', placeholder: '例如：新品首发期/成长期/成熟期'},
        {key: 'budget', label: '预算范围', type: 'input', placeholder: '例如：8万元/月'},
        {key: 'growth_goal', label: '增长目标', type: 'textarea', rows: 2, placeholder: '例如：30天GMV提升40%'},
        {key: 'constraints', label: '约束条件', type: 'textarea', rows: 2, full: true, placeholder: '例如：团队3人，不可增加库存'}
    ], preset: {product_info: '智能手表Pro，售价1299元，主打25-40岁都市白领', target_audience: '一二线城市白领，关注健康和效率', current_stage: '成长期，月销500台', budget: '10万元/月', growth_goal: '30天GMV提升60%，月销突破1500台', constraints: '团队4人，不可增加产品线'}},
    shortvideo: {title: '短视频运营', icon: '🎬', category: 'marketing', desc: '快速生成选题脚本、钩子与发布时间策略。', fields: [
        {key: 'account_positioning', label: '账号定位', type: 'textarea', rows: 3, full: true, required: true, placeholder: '例如：职场技能账号，目标受众为3年以内职场新人'},
        {key: 'content_resources', label: '内容资源', type: 'textarea', rows: 2, placeholder: '例如：已有5条爆款，擅长口播+图文'},
        {key: 'follower_status', label: '粉丝现状', type: 'input', placeholder: '例如：1.2万粉丝，周增200'},
        {key: 'production_capacity', label: '拍摄能力', type: 'input', placeholder: '例如：每天最多拍2条，手机拍摄'},
        {key: 'growth_goal', label: '增长目标', type: 'textarea', rows: 2, placeholder: '例如：7天涨粉5000'},
        {key: 'constraints', label: '约束条件', type: 'textarea', rows: 2, full: true, placeholder: '例如：无专业设备，单人运营'}
    ], preset: {account_positioning: 'AI工具测评账号，帮助打工人提升效率', content_resources: '已有3条千赞视频，擅长实操演示', follower_status: '8000粉丝，完播率35%', production_capacity: '每天1条，电脑录屏+手机拍摄', growth_goal: '7天涨粉3000，3条视频破万赞', constraints: '无出镜，纯录屏+配音'}},
    resume: {title: '简历求职', icon: '🧩', category: 'career', desc: '将经历重写为目标岗位可用的求职材料。', fields: [
        {key: 'personal_experience', label: '个人经历', type: 'textarea', rows: 3, full: true, required: true, placeholder: '例如：3年数据分析经历，主导过用户增长项目'},
        {key: 'target_position', label: '目标岗位', type: 'input', placeholder: '例如：增长策略分析师'},
        {key: 'core_skills', label: '核心技能', type: 'textarea', rows: 2, placeholder: '例如：Python/SQL/Tableau/A/B测试'},
        {key: 'job_goal', label: '求职目标', type: 'textarea', rows: 2, placeholder: '例如：两周内完成投递并拿到面试'},
        {key: 'constraints', label: '约束条件', type: 'textarea', rows: 2, full: true, placeholder: '例如：不夸大经历，强调真实成果'}
    ], preset: {personal_experience: '4年互联网运营经验，主导3个千万级活动，搭建用户增长体系', target_position: '高级用户增长经理', core_skills: '增长黑客/A/B测试/数据分析/社群运营/内容营销', job_goal: '1个月内拿到3个offer，薪资涨幅30%+', constraints: '不夸大经历，突出可量化成果'}},
    business: {title: '商业计划', icon: '📈', category: 'business', desc: '形成市场、商业模式、里程碑与风控方案。', fields: [
        {key: 'project_description', label: '项目说明', type: 'textarea', rows: 3, full: true, required: true, placeholder: '例如：AI客服SaaS项目，面向中型电商企业'},
        {key: 'market_background', label: '市场背景', type: 'textarea', rows: 2, placeholder: '例如：电商客服市场年增长25%'},
        {key: 'competitive_landscape', label: '竞争格局', type: 'textarea', rows: 2, placeholder: '例如：头部3家占据60%份额'},
        {key: 'team_resources', label: '团队资源', type: 'input', placeholder: '例如：5人技术团队+2人销售'},
        {key: 'business_goal', label: '商业目标', type: 'textarea', rows: 2, placeholder: '例如：半年内实现100万ARR'},
        {key: 'constraints', label: '约束条件', type: 'textarea', rows: 2, full: true, placeholder: '例如：初始资金50万，6个月验证期'}
    ], preset: {project_description: 'AI驱动的智能排班SaaS，帮助零售企业优化人力成本', market_background: '零售行业人力成本占比超20%，排班效率普遍低下', competitive_landscape: '传统排班软件3家，无AI驱动产品', team_resources: '3人技术+2人产品+1人销售', business_goal: '6个月100万ARR，签约30家中型零售客户', constraints: '初始资金80万，不可自建数据中心'}},
    dataops: {title: '数据经营分析', icon: '📊', category: 'business', desc: '构建指标、定位异常并给出行动闭环。', fields: [
        {key: 'data_status', label: '数据现状', type: 'textarea', rows: 3, full: true, required: true, placeholder: '例如：近30天渠道转化数据，ROI持续下降'},
        {key: 'business_context', label: '业务背景', type: 'textarea', rows: 2, placeholder: '例如：投放成本上升、留存下降'},
        {key: 'key_metrics', label: '关键指标', type: 'textarea', rows: 2, placeholder: '例如：DAU/转化率/客单价/复购率'},
        {key: 'core_goal', label: '核心目标', type: 'textarea', rows: 2, placeholder: '例如：次月ROI提升20%'},
        {key: 'constraints', label: '约束条件', type: 'textarea', rows: 2, full: true, placeholder: '例如：不可新增人力，预算不增加'}
    ], preset: {data_status: 'Q3营收环比下降12%，获客成本上升35%，老客复购率从42%降至31%', business_context: '行业竞争加剧，新客获取难度增大，老客流失加速', key_metrics: 'CAC/LTV/复购率/NPS/月活/转化率', core_goal: 'Q4止跌回升，ROI提升25%，复购率恢复至38%', constraints: '营销预算不增加，团队维持现有规模'}},
    contract: {title: '合同风险审阅', icon: '⚖️', category: 'professional', desc: '识别高风险条款并给出谈判修改建议。', fields: [
        {key: 'contract_summary', label: '合同摘要', type: 'textarea', rows: 3, full: true, required: true, placeholder: '例如：软件采购合同，总金额120万，交付周期3个月'},
        {key: 'transaction_background', label: '交易背景', type: 'textarea', rows: 2, placeholder: '例如：甲方为大型企业，乙方为初创公司'},
        {key: 'negotiation_position', label: '谈判地位', type: 'input', placeholder: '例如：甲方优势/乙方优势/相对均衡'},
        {key: 'negotiation_goal', label: '谈判目标', type: 'textarea', rows: 2, placeholder: '例如：降低违约风险并明确验收标准'},
        {key: 'constraints', label: '约束条件', type: 'textarea', rows: 2, full: true, placeholder: '例如：维持总价不变，不可更换供应商'}
    ], preset: {contract_summary: 'SaaS平台年度服务合同，总金额80万，含定制开发+1年运维', transaction_background: '我方为采购方，供应商为行业Top3', negotiation_position: '相对均衡，我方有替代方案', negotiation_goal: '明确SLA标准，增加违约赔偿条款，锁定续约价格', constraints: '总预算不可超100万，需在Q1签约'}},
    seo: {title: 'SEO优化', icon: '🔍', category: 'marketing', desc: '关键词策略、站内优化与排名提升方案。', fields: [
        {key: 'website_info', label: '网站信息', type: 'textarea', rows: 3, full: true, required: true, placeholder: '例如：B2B SaaS官网，域名3年，当前日均UV 500'},
        {key: 'industry', label: '行业领域', type: 'input', placeholder: '例如：企业服务/SaaS'},
        {key: 'current_ranking', label: '当前排名', type: 'textarea', rows: 2, placeholder: '例如：核心词排名50+，长尾词有5个在前20'},
        {key: 'competitors', label: '竞争对手', type: 'textarea', rows: 2, placeholder: '例如：A公司/B公司/C公司'},
        {key: 'seo_goal', label: '优化目标', type: 'textarea', rows: 2, placeholder: '例如：3个月核心词进入前10'},
        {key: 'constraints', label: '约束条件', type: 'textarea', rows: 2, full: true, placeholder: '例如：无专职SEO，预算2万/月'}
    ], preset: {website_info: '在线教育平台官网，域名5年，日均UV 2000，移动端占比65%', industry: '在线教育/职业培训', current_ranking: '品牌词第1，行业核心词30-50名，长尾词8个前20', competitors: '竞品A(行业第1)/竞品B(内容矩阵强)/竞品C(外链资源丰富)', seo_goal: '6个月核心词进入前10，自然流量提升200%', constraints: '1人兼职SEO，内容团队3人，月预算3万'}},
    product: {title: '产品需求', icon: '🎯', category: 'professional', desc: '从用户需求到产品落地的全流程设计方案。', fields: [
        {key: 'product_concept', label: '产品概念', type: 'textarea', rows: 3, full: true, required: true, placeholder: '例如：AI驱动的智能日程管理工具'},
        {key: 'target_users', label: '目标用户', type: 'textarea', rows: 2, placeholder: '例如：25-35岁职场白领，日程碎片化'},
        {key: 'core_pain_points', label: '核心痛点', type: 'textarea', rows: 2, placeholder: '例如：日程冲突频繁，优先级难以判断'},
        {key: 'competitor_analysis', label: '竞品分析', type: 'textarea', rows: 2, placeholder: '例如：日历类App功能单一，无智能推荐'},
        {key: 'requirement_goal', label: '需求目标', type: 'textarea', rows: 2, placeholder: '例如：3个月完成MVP上线'},
        {key: 'constraints', label: '约束条件', type: 'textarea', rows: 2, full: true, placeholder: '例如：2人产品团队，技术外包'}
    ], preset: {product_concept: 'AI会议纪要自动生成工具，支持多语言实时转写和智能摘要', target_users: '跨国企业项目经理，每周5+场线上会议', core_pain_points: '会议纪要耗时、遗漏关键决策、多语言沟通障碍', competitor_analysis: 'Otter.ai(英文强)/飞书(生态强但纪要弱)/讯飞(中文强但协作弱)', requirement_goal: '3个月MVP，6个月1.0版本，首年1000企业用户', constraints: '3人技术团队，不可使用需部署的模型'}},
    userresearch: {title: '用户研究', icon: '🔬', category: 'professional', desc: '设计研究方案、访谈提纲与洞察提炼方法。', fields: [
        {key: 'research_topic', label: '研究主题', type: 'textarea', rows: 3, full: true, required: true, placeholder: '例如：新功能使用率低的原因探究'},
        {key: 'target_user_group', label: '目标用户群', type: 'textarea', rows: 2, placeholder: '例如：注册7天内流失的新用户'},
        {key: 'existing_data', label: '现有数据', type: 'textarea', rows: 2, placeholder: '例如：流失用户行为数据+客服反馈'},
        {key: 'research_methods', label: '研究方法', type: 'input', placeholder: '例如：深度访谈+可用性测试'},
        {key: 'research_goal', label: '研究目标', type: 'textarea', rows: 2, placeholder: '例如：找到流失根因并提出改进方案'},
        {key: 'constraints', label: '约束条件', type: 'textarea', rows: 2, full: true, placeholder: '例如：2周内完成，预算5000元'}
    ], preset: {research_topic: '付费转化率从12%降至8%的原因分析与提升策略', target_user_group: '试用期内未转化的免费用户(注册7-14天)', existing_data: '漏斗数据+20条用户反馈+NPS评分45', research_methods: '深度访谈(10人)+问卷调查(200人)+行为数据分析', research_goal: '2周内定位转化流失Top3原因，输出可执行的改进方案', constraints: '预算8000元，2周内完成，不可影响现有用户'}},
    brand: {title: '品牌营销', icon: '💎', category: 'marketing', desc: '品牌定位、传播策略与整合营销方案。', fields: [
        {key: 'brand_status', label: '品牌现状', type: 'textarea', rows: 3, full: true, required: true, placeholder: '例如：新品牌，无知名度，已有基础VI'},
        {key: 'target_audience', label: '目标受众', type: 'textarea', rows: 2, placeholder: '例如：25-35岁都市女性，关注品质生活'},
        {key: 'competitor_brands', label: '竞品品牌', type: 'textarea', rows: 2, placeholder: '例如：A品牌(高端)/B品牌(性价比)'},
        {key: 'brand_tone', label: '品牌调性', type: 'input', placeholder: '例如：温暖/专业/活力/极简'},
        {key: 'marketing_goal', label: '营销目标', type: 'textarea', rows: 2, placeholder: '例如：6个月品牌认知度提升50%'},
        {key: 'constraints', label: '约束条件', type: 'textarea', rows: 2, full: true, placeholder: '例如：预算20万，2人市场团队'}
    ], preset: {brand_status: '新锐护肤品牌，已上线6个月，月销50万，品牌认知度低', target_audience: '25-35岁一二线城市女性，关注成分和功效', competitor_brands: 'A品牌(成分党标杆)/B品牌(平价替代)/C品牌(医美线)', brand_tone: '专业、真诚、有温度', marketing_goal: '6个月内品牌搜索量提升300%，社媒粉丝突破10万', constraints: '月营销预算15万，1人品牌+1人内容'}},
    finance: {title: '财务分析', icon: '💰', category: 'business', desc: '财务健康诊断、模型构建与决策建议。', fields: [
        {key: 'financial_data', label: '财务数据', type: 'textarea', rows: 3, full: true, required: true, placeholder: '例如：年营收2000万，毛利率35%，净利润率8%'},
        {key: 'business_context', label: '业务背景', type: 'textarea', rows: 2, placeholder: '例如：SaaS企业，ARR增长放缓'},
        {key: 'key_assumptions', label: '关键假设', type: 'textarea', rows: 2, placeholder: '例如：客户续约率85%，新客获取成本5000元'},
        {key: 'analysis_dimensions', label: '分析维度', type: 'input', placeholder: '例如：盈利能力/现金流/成本结构'},
        {key: 'analysis_goal', label: '分析目标', type: 'textarea', rows: 2, placeholder: '例如：找出利润率下降原因并给出优化方案'},
        {key: 'constraints', label: '约束条件', type: 'textarea', rows: 2, full: true, placeholder: '例如：不可裁员，维持营收增长'}
    ], preset: {financial_data: '年营收5000万，毛利率60%，净利率从15%降至9%，现金流为正但趋紧', business_context: 'B2B SaaS企业，3年复合增长40%，但增速放缓至20%', key_assumptions: '续约率90%，CAC 8000元，LTV 12万，payback period 14个月', analysis_dimensions: '盈利能力/成本效率/现金流/增长质量', analysis_goal: '净利率恢复至12%+，优化成本结构，提升现金流健康度', constraints: '不可裁员，研发投入不减，6个月见效'}},
    education: {title: '教育培训', icon: '📚', category: 'career', desc: '课程设计、教学活动与评估方案规划。', fields: [
        {key: 'course_topic', label: '课程主题', type: 'textarea', rows: 3, full: true, required: true, placeholder: '例如：Python数据分析入门课程'},
        {key: 'target_learners', label: '目标学员', type: 'textarea', rows: 2, placeholder: '例如：零基础转行数据分析的职场人'},
        {key: 'learner_level', label: '学员水平', type: 'input', placeholder: '例如：零基础/有基础/进阶'},
        {key: 'teaching_resources', label: '教学资源', type: 'input', placeholder: '例如：录播+直播+实战项目'},
        {key: 'teaching_goal', label: '教学目标', type: 'textarea', rows: 2, placeholder: '例如：8周掌握Python数据分析核心技能'},
        {key: 'constraints', label: '约束条件', type: 'textarea', rows: 2, full: true, placeholder: '例如：每周2次课，每次1.5小时'}
    ], preset: {course_topic: 'AI应用实战课：从Prompt Engineering到AI工作流搭建', target_learners: '1-3年职场人，希望用AI提升工作效率', learner_level: '零基础，会使用电脑和浏览器', teaching_resources: '录播视频+在线练习+社群答疑+实战项目', teaching_goal: '6周掌握5大AI工具深度使用，独立搭建3个AI工作流', constraints: '每周3次课，每次1小时，无编程要求'}}
};
})();
