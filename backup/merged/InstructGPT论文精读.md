# InstructGPT论文精读

## **用人的反馈引导大规模语言模型变得更有价值**

## **InstructGPT论文精读**

### **模型：有监督+增强学习**

模型中各个任务的backbone都是GPT-3的架构，支持的context length是2k的token（其中数据处理中prompt选择不超过1k，response不超过1k）【chatGPT的context长度更长】

1. **Step1：有监督学习(SFT)，Supervised Fine-tuning**：在GPT-3的基础上用人工标注的prompt-reponse进行finetune，几个有意思的细节
- a. 16epoch，基本是overfitting，但是效果却更好
- b. 用RM Score来做选点而非validation的metrics

**2. Step2：强化学习**

**2.1 生成问题的强化学习建模**

![v2-96b7082ee920eb8f261f3e715a4098eb_1440w.jpeg](InstructGPT%E8%AE%BA%E6%96%87%E7%B2%BE%E8%AF%BB.assets/v2-96b7082ee920eb8f261f3e715a4098eb_1440w.jpeg)

如上图所示，文本生成的问题，可以建模为一个token空间上的序列决策问题（选择一个token后继续选择另一个token）

- state：context
- action：reponse的token space上的token
- reward：生成的质量判别
- episode：一次完整的decode生成response的过程

RLHF中通过人工标注生成结果的排序数据中学习和建立reward模型，进而把human对结果质量的判断引入到生成模型中。而生成模型就对应的是Policy模型，通过学习和调整policy模型就是在做生成模型的finetune。

**2.2 奖励模型(Reward model)**

- **SFT Model为基础**，6B规模（175B规模的太大，不太稳定）(以GPT-3 6B的差别也不大)
- **任务**：给定prompt，response出分档的打分
- **Loss**：一个prompt内的N个response的pairwise-loss

**2.3 PPO模型及训练**

PPO（Proximal Policy Optimization[2]）是RL中AC类(Actor/Critic)的经典算法，既有Policy Gradient方法的优势，同时基于importance sampling实现experience buffer的利用，发挥类似DQN类算法的数据利用优势，OpenAI非常喜欢用来作为baseline的算法。该算法的具体细节就不展开介绍，感兴趣的可以阅读原论文。

- **Policy(Actor)起点模型**：Step1中的SFT模型
- **Reward模型**：2.2中的模型
- **Value模型(Critic)：**初始化自Reward模型
- **数据：**经过实验发现，全部使用线上真实的Prompt数据+Reward模型(3.1W)会导致模型在人工评估中效果好，但是损失在开放的NLP任务测试集上的效果（作者称之为alignment tax），最后采用的是10%的预训练数据保留+PPO Training，这种混合的模型，作者称之为PPO-ptx
- PPO Training loss + pretrain loss + KL Pernalty(正则，防止RL overfit)
- pretraning样本：RL样本 = 8：1
- Loss及目标函数

![v2-4972a9ce168f322090e42480a2645224_1440w.png](InstructGPT%E8%AE%BA%E6%96%87%E7%B2%BE%E8%AF%BB.assets/v2-4972a9ce168f322090e42480a2645224_1440w.png)

### **魔鬼的细节：human feedback的数据构建**

整体而言人工标注的数据量级比想象中的小(万级别)，但是质量、数据分布、不同阶段的数据标注方式等设计十分精细，再次体现了OpenAI研究员们非常落地的做事风格也体现数据作为模型效果燃料的关键之关键（不少人也认为之前的GPT-3比同期的不少社区开源的同级别参数量的预训练模型效果好也很大程度来自于其精细化的训练数据构建和数据处理）。

**1. 40个精心挑选的标注员**

- screen test：为了保证标注的质量，设计了测试来筛选标注人员，主要包含几个部分
- i. 识别不安全回复的能力
- ii. 回复质量排序能力
- iii. 敏感问题的回复能力：1-7分的打分及平均
- iv. 按照不同的人群和文化进行分组

**2. 标注数据来源：Prompts的数据来源及类型**

- a. 人工撰写，三种类型的数据
- i. plain：直接给出需求问题，比如：世界上最大的河是什么？
- ii. few-shot：即给出一些问题和结果示例，再带上新的问题，比如：问：世界上最高的山？答：世界上最高的山是喜马拉雅山，问：世界上最长的河是？
- iii. user-based：根据一些use case场景进行设计
- b. Open AI之前GPT-3等开放模型中的API请求（相当于真实的线上Query）为了保证多样性
- i. 对相同的prompt前缀进行去重
- ii. 每个机构限制采样数量（200）

**3. 标注的任务及目标**

- a. 构造和撰写一些prompt并且写出对应的结果–for SFT任务
- b. 针对给定的prompt，撰写对应的结果 --- for SFT任务

![v2-95d3aa9f57ccf365d3fbb1b15431d5fc_1440w.webp](InstructGPT%E8%AE%BA%E6%96%87%E7%B2%BE%E8%AF%BB.assets/v2-95d3aa9f57ccf365d3fbb1b15431d5fc_1440w.webp)

- 针对给定的prompt、模型给出的多个结果，标注结果的好坏排序 --- for Reward Model

![v2-840050aefd3e48da9cf1d950fe619231_1440w.webp](InstructGPT%E8%AE%BA%E6%96%87%E7%B2%BE%E8%AF%BB.assets/v2-840050aefd3e48da9cf1d950fe619231_1440w.webp)

**4. 标注的标准，三个维度：有用(Helpful)、真实(truthful)、无害(harmless)**

- a. **Helpful**：意图理解精准，能够对模糊的需求提出澄清以及解释为什么模糊，结果描述清晰，没有反复重复的无用词汇等
- b. **Truthful**：正确、真实（不同场景下有所不同，比如 closed q&a或者summarization，则不应该跳出参考的信息进行编造）
- c. **Harmless**：无害，包括黄色、暴力、歧视、敏感政治回答等各类不合理有争议的言语

**5. 标注的数据量及各个任务的训练数据量**

- a. SFT任务中人工撰写的prompt占比较高（1.3w）
- b. RM任务中以真实的prompt为主（3.3w）
- c. PPO任务完全以真实的prompt为主（3.1w）

![v2-3aceba1b5dfed32d6f2b9f2a511401d7_1440w.webp](InstructGPT%E8%AE%BA%E6%96%87%E7%B2%BE%E8%AF%BB.assets/v2-3aceba1b5dfed32d6f2b9f2a511401d7_1440w.webp)

数据类型中包含了不少模糊的、不清晰意图的、敏感内容等。

![v2-c74235fcf70d71bb3d36e981a1166c18_1440w.webp](InstructGPT%E8%AE%BA%E6%96%87%E7%B2%BE%E8%AF%BB.assets/v2-c74235fcf70d71bb3d36e981a1166c18_1440w.webp)

### **评估和实验结论**

**1. 实验评估和验证的方式**

- a. 数据集
- i. 真实的prompt数据
- ii. 公开的NLP任务：包含一些是否真实结果的数据集TruthfulQA，是否有害回复的Realtoxicityprompts等
- b. 评估方式
- i. 人工标注的打分分档，问题细分
- ii. 模型对比：以175B的SFT为对标，看人工对结果质量打分的GSB(Good/Same/Bad)
- iii. 其他公开NLP任务的数据集自动指标

**2. 关键和有启发性的一些实验结论**

- a. 在生成的回复质量的人工评估上，GPT-3->+SFT->+PPO的效果逐级变好，**PPO的表现作为优异，1.3B的模型规模上就能beat SFT 175B的模型**
- b. 表现出很强的泛化能力，在没有见过的测试集上依然效果很好

![v2-f0894b7b4fc9d079c28b14c463955433_1440w.webp](InstructGPT%E8%AE%BA%E6%96%87%E7%B2%BE%E8%AF%BB.assets/v2-f0894b7b4fc9d079c28b14c463955433_1440w.webp)

- c. **公开的instruct类的数据集有用但是并不能完全体现真实场景下语言模型的使用（这点非常重要，不如OpenAI线上用户使用的Prompt价值高，数据价值再次显现）**
- 训练成本，SFT：0.49PFlops/s-days vs RLHF：60PFlops/s-days vs GPT-3 175B：3640 PFlops/s-days
- 其中1PFlops/s-days在175B规模的模型下大概对应8卡 V100/天（A100虽然算力更好，但是显存依然无法突破限制）
- 用FLAN和T0（刚好怼一波G厂Flan-T5）的数据集做SFT相比GPT-3有效果，但是不如用OpenAI自己数据训的（当然评估的数据集也是OpenAI的customer prompt）
- 两个原因：1）真实的prompt中有比较多比例开放式的问题（头脑风暴类的），由于没有客观答案，往往公开数据集不太会纳入 2）公开数据集没有很好的条件收集到足够多样性的数据
- 在truthful上instructGPT大幅提升，避免有害信息上小幅提升
- **instructGPT(+PPO)表现出非常强的训练集外的泛化能力，尤其是的的的的泛化能力（训练的语料中，尤其是SFT/RM/RLHF，非英文语言的语料比例非常少，但是却表现出很强的其他语言的能力，在我们测试的中文场景下也能看到）。反过来说，跨语言的语料的学习也应该同样有可能带来整体效果性能的提升**
- f. **训练成本远低于预训练，相比于继续增大预训练模型的参数规模Alignement是一个更具性价比且正确的方向**

## **ChatGPT实现推测**

ChatGPT官方并没有像instructGPT那样给出详细的实现论文，仅有官网Blog[11]上比较概要性的描述，以下通过这些描述来尽量推测其实现的一些细节。

> ChatGPT is fine-tuned from a model in the GPT-3.5 series, which finished training in early 2022. You can learn more about the 3.5 series here.
ChatGPT的底座模型，如上述，**是GPT 3.5系列，基于推测至少可能是text-davinci-002（即既有text能力又有code能力）**

> We trained this model using Reinforcement Learning from Human Feedback (RLHF), using the same methods as InstructGPT, but with slight differences in the data collection setup.
整体的技术方案和InstructGPT类似，并且官网的blog中给的图也和instructGPT论文中的示例图相似，**于是显然数据的构造、标注的方式成为关键，尤其是如何构造对话的语料**。

## **对话语料的构造推测**

以如果是我在这个设定下去考虑构造对话语料训练出拥有这类对话能力的模型，我该怎么去构造语料出发，来思考。整个RLHF的训练涉及到3个关键阶段：

**1. 有监督的微调（SFT：Supervised Finetune）**

![v2-8e1d40487b9852c4b61fc524b582c544_1440w.jpeg](InstructGPT%E8%AE%BA%E6%96%87%E7%B2%BE%E8%AF%BB.assets/v2-8e1d40487b9852c4b61fc524b582c544_1440w.jpeg)

> We trained an initial model using supervised fine-tuning: human AI trainers provided conversations in which they played both sides—the user and an AI assistant. We gave the trainers access to model-written suggestions to help them compose their responses. We mixed this new dialogue dataset with the InstructGPT dataset, which we transformed into a dialogue format.
语料构成：人工交互标注产生 + instructGPT转化为对话语料 **Q：如何人工标注产生对话语料？**  两个标注人员分别作为用户以及AI进行对话，那么对话的起点以及场景从哪里来，从instructGPT的数据构造参考的话，可以有两种：

1. 场景构造，然后开始自由发挥
2. 开头的prompt基于线上API请求中的抽样，后面的多轮对话过程按照人工标注的思路开展

值得注意的是应该构建**不只一个需求的对话过程，包含一些插入、多个需求等复杂的场景情况**。

而其中chatBOT的标注人员的回复策略以及user的回应的策略、采样的数据等，根据最终期望模型获得能力需要有精心的设计。其中回复的策略对照chatGPT的能力以及理想对话中的action strategy应该有几种

1. **follow the instruction**：按照用户的需求直接给满足的response，这个和instructGPT中类似
2. **clarify**：对于模糊的需求进行澄清和询问。
3. **admit the mistakes**：要求user侧应该能够指出response的错误，同时chatBOT侧的标注人员能够根据指出的错误进行回复和答案的修改
4. **challenge the premise**：对于不符合逻辑的问题，chatBot侧的标注人员能够生成对不合理逻辑的挑战和解释的答案
5. **reject inappropriate requests**：对于边界的问题和不安全的问题，不回复（数据的抽样以及标注人员的回复策略都需要对应的设计）

另外，从多轮的一些指代消解维度来看，抽样的数据和对话语料构建的过程中也应该可以仿照对话的一些维度的能力进行标注的引导和数据分布的均衡：Query中指代、结果中指代等。

**Q：instructGPT中的数据转化为对话的语料？**

instructGPT中都是单轮的Prompt-Response的语料，要转化为对话的语料。能想到的最简单的是把单轮的语料做一些随机的组合形成一些对话的语料，这种组合出来的对话语料可以体现用户不同的需求切换，在对话场景中依然能够正确的理解。但是如果只是这样子的话，感觉并没有充分的利用起来，如果可以的话，应该可以对其中的一些原本的prompt就属于模糊需求、有错误的、边界能力以及不安全类的挑出来，再过人人交互的对话标注方式进行延展产生这些场景下更丰富的多轮语料。

**2. 奖励模型（RM，Reward Model）**

RM的标注数据在instructGPT中主要是对一个prompt下的不同response标注结果的质量排序，而对话中需要把prompt换成一个context。

> To create a reward model for reinforcement learning, we needed to collect comparison data, which consisted of two or more model responses ranked by quality. To collect this data, we took conversations that AI trainers had with the chatbot. We randomly selected a model-written message, sampled several alternative completions, and had AI trainers rank them.
上述的描述中，有个细节是用标注人员与chatbot的交互中的某一轮，展开来看对应的多个结果，让标注人员进行结果的质量排序。那么这个时候的chatbot用什么模型，最原始的底座模型显然没有对话能力。所以我推测应该是在第一步SFT之后。 **3. 增强学习训练（with PPO）**

> we can fine-tune the model using Proximal Policy Optimization. We performed several iterations of this process.
用PPO进行finetune，这块的数据instructGPT中完全采用的是线上API的prompt，但那里面更多的应该都还是单轮的。我翻看了下，也有很多GPT-3之后下游的生态中用来做chatbot的，所以应该可以从这个里面抽取数据。当然也可以采用之前人工标注数据中起点的prompt从线上来人人对话继续延展产生的对话语料。

## **References**

1. OpenAI官网：[https://openai.com/](https://link.zhihu.com/?target=https%3A//openai.com/)
2. instructGPT：[https://arxiv.org/abs/2203.02155](https://link.zhihu.com/?target=https%3A//arxiv.org/abs/2203.02155)
3. ChatGPT，[https://openai.com/blog/chatgpt/](https://link.zhihu.com/?target=https%3A//openai.com/blog/chatgpt/)