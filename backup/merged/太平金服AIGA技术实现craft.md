# 太平金服AIGA技术实现craft

# 一、use case (To C千万级用户)

1、保险故事场景

（1）我有哪些保单？

返回：保单列表，包括寿险、财险、养老等

（2）我的寿险保单最迟什么时间续费？

返回：编号xxx寿险缴费日是2023年10月1日，最迟请在2023年11月1日前完成续费。

（3）我想给太太买份保险，有什么产品推荐的吗？

返回：家庭风险分析，太太风险补漏，以及计划书

（4）这款寿险产品与某某公司寿险产品有什么特点？

返回：针对客户家庭情况，推荐您太太需要增加20万寿险保额，本款产品最适合；某某公司寿险产品，大大超过所需的寿险保额，代价较大

（5）我的车险需要续费，如何缴费？

返回：续费支付链接、二维码或按钮，直接微信或支付宝缴费

（6）**我朋友需要购买车险，有优惠活动吗？**

**返回：返回车险产品链接，2023年10月1日前购买，价格打9折；推荐人员送1000金币，可以兑换50元话费。**

**（7）我的车需要充电**

**返回：地图，可以全屏显示周围充电桩**

**（8）去A充电桩**

**返回：地图导航**

2、投资端故事场景

（1）查看我现在资产情况

返回：保单现金价值、基金、资管产品、平台金币以及负债（信贷）

（2）收益率高的个人养老金产品有哪些？

返回：福享今生进取型，高档结算利率预估6%

（3）查询保证利率最高的个人养老金

返回：福享今生稳健型，保证利率3%，写在合同中

（4）我有1万元零钱，有哪些货币基金推荐？

返回：太平基金对应的货币基金列表

（5）购买A款1万元

返回：购买成功

（6）**我有100万资金，稳定年化增值5%的产品有哪些？**

**返回：推荐资管产品列表**

**（7）我需要5万现金，急用**

**返回：实时贷产品**

**（8）我需要20万信贷，1年后还本金**

**返回：客户信用较好，推荐中信银行“信秒贷”，年后单利利率低至4.68%起；**

3、活动端故事场景

多轮对话：

（1）**近期有什么获取金币的活动？**

**返回：中国太平二十大主题知识竞赛，最高获得1000金币**

**（2）我的金币可以兑换哪些商品？**

**返回：可兑换商品列表**

**（3）兑换50元话费**

**返回：兑换成功**

（4）我要投诉，我的金币怎么少了？

返回：金币有效期一年，截止上月您有1000金币过期了。

（5）近期有投资方面的直播活动吗？

返回：“洞见价值、探索资产配置直播节目”

（6）有基金方面的吗？

返回：基金第一课直播回放链接

4、其他

1. 我要退保，能退多少钱？
2. 我同时有寿险、财险和养老险的问题咨询，过去需要分别客服专业回答，新的形式下可以统一回答。

# To A（保险代理），数十万级用户

保险代理辅助销售工具

目前保险代理**有一系列日常工作，要在不同app内应用中跳转，而需求又是个性化**的

1. **帮我拉一下最近一个月保费到期的客户名单，并给他们发提醒短信**
2. **保额100万的客户，本周有谁过生日，发送新产品宣传链接**
3. **客户问，太平的产品A和泰康的产品B相比有什么优势和特点**
4. 根据客户情况，生成保险计划书

# To Indus（行业，经纪公司），百万级用户

1. 保险代理人过去都是以保司利益为先的，保司哪个产品提成高，推哪个
2. 真实的市场需求是 保险经纪人能站在客户的立场上，帮助客户综合市面上所有产品，选出最佳的单品或组合。这需要**收集所有保险产品说明，然后根据不同的需求** 给出保险建议。
    1. 和阅读财报有些像，**能够总结关键点，还能给出出处**。

# To E（企业内部），万级用户

1. 企业办公场景，太平目前内部的移动办公工具是自研的（非飞书、企业微信、钉钉）；
2. 企业知识中心。

# 二、交互示意图

暂时无法在数字大脑文档外展示此内容

## 现状

# 三、价值

**以ToC为例**

![Image (2).jpeg](%E5%A4%AA%E5%B9%B3%E9%87%91%E6%9C%8DAIGA%E6%8A%80%E6%9C%AF%E5%AE%9E%E7%8E%B0craft.assets/Image%20(2).jpeg)

# 四、实现示意图

![Image (3).jpeg](%E5%A4%AA%E5%B9%B3%E9%87%91%E6%9C%8DAIGA%E6%8A%80%E6%9C%AF%E5%AE%9E%E7%8E%B0craft.assets/Image%20(3).jpeg)

> transformer压缩知识，instruction整理知识（符号映射方式获得语义理解） ；

> 增强推理： In-context ，代码，COT联结上action。

# 五、关键技术点

## 1、与机器人倒咖啡任务的比较

#### **相似点：**

- 自然语言的方式下命令，自动的理解和planning，生成代码，调用API；

#### **不同点：**

- 行业特点的任务与commonsense reasoning不同，大模型如何理解，然后进行决策(任务分解)。

#### **需要做什么？**

- 行业任务，大模型缺少相关知识，如何解？

    >> 把知识显性的加入到in-context，是步骤之一。

    >> 每个API的example，作为样本，进行SFT，让它学会。

- 怎么增强推理能力？

**与EVA** **demo** **task的区别**

Can you help me set up a new delivery address? The receiver's name is xx, and their phone number is xxxx.

The address is xxx, and I would like to make it my default delivery address.

## 2、Reasoning

模型规模的提高，让**语义理解、符号映射、连贯文本生成等能力跃升**，从而让多步骤推理的思维链成为可能

### 2.1 策略增强

主要目的是设计更好的推理策略来增强大模型的推理表现。

#### 2.1.1 提示工程

![Image.png](%E5%A4%AA%E5%B9%B3%E9%87%91%E6%9C%8DAIGA%E6%8A%80%E6%9C%AF%E5%AE%9E%E7%8E%B0craft.assets/Image.png)

#### 单阶段方法

大多采用**基于模板的提示**进行推理。

- 强大的In-context Learning能力，添加了被称为思维链的中间推理步骤到few shot 中，来诱导LLM更好地完成推理。
- 除了少样本推理外,zero shot,仅需要在问题后拼接"Let's think step by step"作为提示。

#### 多阶段方法

把一个复杂的问题分解成更简单的子问题，逐个进行推理解决。

同样，多阶段方法旨在将之前的单阶段提示转变为多阶段提示。

- Maieutic prompt 方法**将每一阶段的输出视作单独的新问题；**
- Least-to-most prompt 和 Iteratively prompt方法**将每一阶段的输出附加到上下文中来**提示LLM；
- Decomposed prompt 方法则将**任务分解为多个*分离*和*合并*子任务，并为解决每个子任务设计特定的提示**。

#### 2.1.2 推理过程优化

![Image (2).png](%E5%A4%AA%E5%B9%B3%E9%87%91%E6%9C%8DAIGA%E6%8A%80%E6%9C%AF%E5%AE%9E%E7%8E%B0craft.assets/Image%20(2).png)

#### 自优化

**引入一个参数化的优化器在生成答案 时校准推理依据** ，这类工作可以称为自优化方法

自优化方法通过引入额外模块来纠正推理过程。

- 在生成文本推理依据时，Human-AI 方法**微调了一个 Seq2seq 模型作为过滤器，以预测生成的推理依据是否可以接受。**

#### 集成优化

为了缓解单一推理路径的限制，集成优化方法在多个推理路径之间进行集成校准：

- DIVERSE 方法：提出了一个步骤感知的投票检验器来对每个推理路径进行评分，当错误的推理路径多而正确的推理路径少时，步骤感知的投票检验器可以缓解简单多数投票的限制。
- 迭代优化：使用LLM微调,迭代地校准推理过程。
    - **STaR 方法从较小的一组范例开始，推动LLM生成推理步并自己回答，正确答案的问题和推理步将直接添加到用于微调的数据集中。** **[https://openreview.net/pdf?id=_3ELRdg2sgI](https://openreview.net/pdf?id=_3ELRdg2sgI)**

![Image (3).png](%E5%A4%AA%E5%B9%B3%E9%87%91%E6%9C%8DAIGA%E6%8A%80%E6%9C%AF%E5%AE%9E%E7%8E%B0craft.assets/Image%20(3).png)

#### 2.1.3 外部推理引擎

模型同时具有语义理解和复杂推理（例如生成推理过程）的能力，但往往鱼和熊掌不可兼得。为了解决这种障碍，预训练语言模型还可以借助外部推理引擎进行推理。

- 物理模拟器：给定一个物理推理问题，Mind’s eye 方法[15]**利用一个物理计算引擎来模拟物理过程。模拟结果可以作为提示**，弥补了预训练模型物理知识的不足。
- 代码解释器：程序和代码在鲁棒性和可解释性方面具有天然优势，并且可以更好地说明复杂的结构并推导复杂的计算。
    - PAL 方法：
        - [https://github.com/reasoning-machines/CoCoGen](https://github.com/reasoning-machines/CoCoGen)
        - [https://github.com/reasoning-machines/pal](https://github.com/reasoning-machines/pal)

### 2.2 知识增强

#### 2.2.1 隐式知识

LLM**中包含了相当多的隐式知识，这些知识可以通过条件生成来引出作为知识提示来增强推理。**

- [Rainier: Reinforced Knowledge Introspector for Commonsense Question Answering](https://aclanthology.org/2022.emnlp-main.611.pdf)

随着模型规模的增加，少样本提示几乎在各项任务中都有更好的表现，这可以**解释为更大规模的模型蕴含更多用于推理的隐式知识。**

不同于上述方法在生成阶段只采用少样本提示

- TSGP 方法提出了一个**两阶段的生成提示，其中还包括答案生成提示**。
    - first use knowledge generation prompts to generate the knowledge required for questions with unlimited types and possible candidate answers independent of specified choices.
    - Then, we further utilize answer generation prompts to generate possible candidate answers independent of specified choices.
- 使用大规模教师模型上的思维链输出在小规模学生模型上进行微调，实现了推理能力的迁移。[https://arxiv.org/pdf/2212.08410.pdf](https://arxiv.org/pdf/2212.08410.pdf)
    - (1) generate CoT for existing datasets using LLMs ；
    - (2) finetune smaller LMs on the CoT.

#### 2.2.2 显式知识

- PROMPTPG, for few-shot GPT-3, which utilizes policy gradient to learn to select in-context examples from the training data and construct the performing prompt for the test example.
    - [https://openreview.net/pdf?id=DHyHRBwJUTN](https://openreview.net/pdf?id=DHyHRBwJUTN)
- 通过选择少量标注样本，可以持平大规模标注样本或随机标注样本得到模型的表现能力 vote-k [https://taoyds.github.io/](https://taoyds.github.io/)
- One Embedder, Any Task: Instruction-Finetuned Text Embeddings [https://arxiv.org/pdf/2212.09741.pdf](https://arxiv.org/pdf/2212.09741.pdf)
    - 可以用在prompt retrieve

**输入上下文中，显式包含高质量推理依据是大模型提示推理的关键；**

### 2.3 一些技巧

- 增加long term的记忆
- 生成子实例完成不同的任务
- 自动纠正错误的返回，然后重新修正
- fine-tunes a sequence-to-sequence model as a filter to predict whether the rationale is acceptable.

## 3、大模型和推荐的结合

1、多轮对话中，自动的提示和引导用户提问

- 意图能够较好的被识别；
    - [https://arxiv.org/pdf/2210.05901.pdf](https://arxiv.org/pdf/2210.05901.pdf) Zero-Shot Prompting for Implicit Intent Prediction and Recommendation with Commonsense Reasoning
    - [https://arxiv.org/pdf/2203.08568.pdf](https://arxiv.org/pdf/2203.08568.pdf) In-Context Learning for Few-Shot Dialogue State Tracking
- 多步流程，使用prompt模版方式；

2、对话过程中，其他产品和功能的推荐。因为对话过程中，需求越来越明确。

**AutoGPT对比**

1. 使用列表保存历史发送的信息，并在每一次请求token允许的条件下**发送最多的历史消息给GPT-4；**
2. 每一次发送请求的时候，它**都会让GPT知道现在的一些时间等情景信息，方便处理与时间有关的内容；**
3. 每一次都**将当前最相关的目标也发送给GPT-4**。AutoGPT**保存了所有的历史信息，在每一次查询的时候也会把当前实例最相关的信息也发给GPT-4**。

## 4、专有大模型/行业大模型

- 为什么需要专有大模型
    - 数据泄露问题。
        - 训练过程中，上传数据，进行FInetune，
        - 使用过程中，三星泄露了
- 专有大模型需要在通用大模型的基础上，有哪些不同呢？
    - 使用了行业数据预训练，例如华佗。加入更多的行业数据，能够直接回答通用大模型里不知道的问题。
        1. 会有缺点，过多的专业知识，“偏科”，会导致忘记其他技能。
    - 不进行预训练，只是进行SFT
        1. 比如特定格式的输出，例如病历；
        2. 预训练和外挂知识库对比： 预训练的语义理解能力更强。外挂知识库，retrieve过程和大模型理解总结过程，需要足够的准确。
- 哪些相同
    - 大模型的语言理解能力
- 更重要的是，由于大模型是和业务紧密结合的， **能够随时按照需求，自己定制训练大模型的能力**，必不可少。

## 5、行业知识中心

- 企业内部丰富的知识，没有得到有效的利用。
- 只需要将知识通过模型理解，打造一个超越于人脑和彻底变革过去知识库的知识中心。

## 6、行业API能力中心

即action center：

所有的功能只需要在能力中心注册，提供以下信息，即可完成触达到用户。

- 功能描述；
- 卡片样式选择；
- 接口输入输出描述
- example

强大 不同之处

开篇

- 当前app这样运营模式
- 未来的是什么样
- ToC 对比

展示核武器

展示→ 需要实现的核心东西

\--

知识库 → 知识中心

路径：

先使用的开源的哪个模型

\-->

最终，架构

两个版本

- 技术
- 业务人

要实现什么？

放到后面

画图 --→ 业务

技术方案

- 细节比较。。  不同点

交互ToC

- 从客户角度

能力的增强， 和通用方式比较。

Toc

1、

TOa

2、

先PPT 得到反馈。

行业资料、论文、测试数据。

方案越来越成熟。