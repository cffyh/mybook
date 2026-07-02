# 想自己利用OpenAI做一个文档问答的话......

​

野生工程师，要说不务正业，还真是不务正业！

​关注他

108 人赞同了该文章

​

目录

收起

1 [document.ai](http://document.ai)

1.1 ChatGPT Embedding使用框架

1.2 工程化中的一些优化点

2 利用ChatGPT 和Milvus快速搭建智能问答机器人

2.1 ChatGPT API简述

2.2 整体架构

3 llama-index(gpt-index)对话式文档问答解决方案

3.1 任务描述和问题分析

3.2 解决思路

3.3 代码案例

4 loli.xing 基于 ChatGPT 的客服系统

5 Document_QA

6 ChatWeb

7 chatpdf-minimal-demo

本篇举几个例子来说明如何利用OpenAI Embedding做文档问答，如何进行工程化，工程化的难点与步骤有些什么。了解类似ChatPDF这样应用的实现原理。为后续自己搞一个做预调研！

---

## 1 [document.ai](http://document.ai)

### 1.1 ChatGPT Embedding使用框架

基于向量数据库与GPT3.5的通用本地知识库方案(A universal local knowledge base solution based on vector database and GPT3.5)

![v2-87c638e42a03297583eb64c7ce63cddd_1440w.png](%E6%83%B3%E8%87%AA%E5%B7%B1%E5%88%A9%E7%94%A8OpenAI%E5%81%9A%E4%B8%80%E4%B8%AA%E6%96%87%E6%A1%A3%E9%97%AE%E7%AD%94%E7%9A%84%E8%AF%9D.......assets/v2-87c638e42a03297583eb64c7ce63cddd_1440w.png)

流程：

- 将本地答案数据集，转为向量存储到向量数据
- 当用户输入查询的问题时，把问题转为向量然后从向量数据库中查询相近的答案topK 这个时候其实就是我们最普遍的问答查询方案，在没有GPT的时候就直接返回相关的答案整个流程就结束了
- 现在有GPT了可以优化回答内容的整体结构，在单纯的搜索场景下其实这个优化没什么意义。但如果在客服等的聊天场景下，引用相关领域内容回复时，这样就会显得不那么的突兀。

### 1.2 工程化中的一些优化点

> 问答拆分查询
在上面的例子中，我们直接将问题和答案做匹配，有些时候因为问题的模糊性会导致匹配不相关的答案。
如果在已经有大量的问答映射数据的情况下，问题直接搜索问题集，然后基于已有映射返回当前问题匹配的问题集的答案，这样可以提升一定的问题准确性。

> 抽取主题词生成向量数据
因为答案中有大量非答案的内容，可以通过抽取答案主题然后组合生成向量数据，也可以在一定程度上提升相似度，主题算法有LDA、LSA等。

> 自训练的Embedding模型
openAI 的Embedding模型数据更多是基于普遍性数据训练，如果你要做问答的领域太过于专业有可能就会出现查询数据不准确的情况。
解决方案是自训练 Embedding 模型，推荐一个项目 [text2vec](https://link.zhihu.com/?target=https%3A//github.com/shibing624/text2vec)

> 基于 Fine-tune
目前自身测试下来，使用问答数据集对GPT模型进行Fine-tune后，问答准确性会大幅提高。你可以理解为GPT通过大量的专业领域数据的学习后成为了该领域专家，然后配合调小接口中`temperature`参数，可以得到更准确的结果。
但 现在 Fine-tune 训练和使用成本还是太高，每天都会有新的数据，不可能高频的进行 Fine-tune。一个想法是每隔一个长周期对数据进行 Fine-tune ，然后配合外置的向量数据库的相似查询来补足 Fine-tune 模型本身的数据落后问题。

[https://github.com/GanymedeNil/document.ai​github.com/GanymedeNil/document.ai](https://link.zhihu.com/?target=https%3A//github.com/GanymedeNil/document.ai)

---

## 2 利用ChatGPT 和Milvus快速搭建智能问答机器人

### 2.1 ChatGPT API简述

ChatGPT以文字方式互动，除了可以透过人类自然对话方式进行交互，还可以用于相对复杂的语言工作，包括自动文本生成、自动问答、自动摘要等在内的多种任务。

ChatGPT 是由 OpenAI 最先进的语言模型 gpt-3.5-turbo 提供支持， GPT-3.5-turbo 模型是以一系列消息作为输入，并将模型生成的消息作为输出。

```other
# Note: you need to be using OpenAI Python v0.27.0 for the code below to work
import openai

openai.ChatCompletion.create(
  model="gpt-3.5-turbo",
  messages=[
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "Who won the world series in 2020?"},
        {"role": "assistant", "content": "The Los Angeles Dodgers won the World Series in 2020."},
        {"role": "user", "content": "Where was it played?"}
    ]
)
```

消息是一个对象数组，其中每个对象都有一个角色，一共有三种角色。

- **系统** 消息有助于设置助手的行为。在上面的例子中，助手被指示 “你是一个得力的助手”。
- **用户** 消息有助于指导助手。 就是用户说的话，向助手提的问题。
- **助手** 消息有助于存储先前的回复。这是为了持续对话，提供会话的上下文。

我们调用的ChatGPT的API是无状态的，意味着你需要自己去维持会话状态，保存上下文，每次请求的时候将之前的历史消息全部发过去，但是这里面有两个问题：

1. 为了建立持续会话，请求内容会越来越大，这些内容前后的关联关系并不是很大；
2. 语言模型以称为 tokens 的块读取文本，需要为为每个 token 支付费用，这样Token 费用很高。
3. 为了保证API调用的有效性，令牌总数必须是 低于模型的最大限制（gpt-3.5-turbo-0301 为 4096 个令牌）

我们借助OpenAI的embedding模型和自己的数据库，先在本地搜索数据获得上下文，然后在调用ChatGPT的API的时候，加上本地数据库中的相关内容，这样就可以让ChatGPT从你自己的数据集获得了上下文 ，再结合ChatGPT自己庞大的数据集给出一个更相关的理想结果。

### 2.2 **整体架构**

本文通过语义相似度匹配来实现一个问答系统，大致的构建过程：

1. 获取某一特定领域里大量的带有答案的中文或者英文问题（本文将之称为标准问题集），把它变成CSV或者Json这样易于处理的格式，并且分成小块（chunks），每块不要超过8191个Tokens，因为这是OpenAI embeddings模型的输入长度限制。
2. 使用OpenAI的embedding模型将这些问题转化为特征向量，需要将转换后的结果保存到本地数据库。 注意一般的关系型数据库是不支持这种向量数据的，需要使用向量数据库，这里使用Milvus，同时Milvus将给这些特征向量分配一个向量ID。
3. 当然你保存的时候，可以把原始的文本块和数字向量一起存储，这样可以根据数字向量反向获得原始文本。也可以将这些代表问题的ID和其对应的答案存储在关系数据库SQL Server/Postgresql中, 这一步有点类似于全文索引中给数据建索引。

当用户提出一个问题时：

1. 通过OpenAI的embedding模型将之转化为特征向量
2. 在Milvus中对特征向量做相似度检索，得到与该问题最相似的标准问题的id, 拿到这个数字向量后，再去自己的数据库进行检索，那么就可以得到一个结果集，这个结果集会根据匹配的相似度有个打分，分越高说明越匹配， 这样就可以按照匹配度倒序返回一个相关结果。
3. 在PostgreSQL得出对应的结果集。然后根据拿到的结果集，将结果集加入到请求ChatGPT的prompt中。

系统交互图来自宝玉的微博（[https://m.weibo.cn/status/4875446737175262](https://link.zhihu.com/?target=https%3A//m.weibo.cn/status/4875446737175262)）如下：

![v2-2ba61e715919d5ab02a521c55f512b93_1440w.webp](%E6%83%B3%E8%87%AA%E5%B7%B1%E5%88%A9%E7%94%A8OpenAI%E5%81%9A%E4%B8%80%E4%B8%AA%E6%96%87%E6%A1%A3%E9%97%AE%E7%AD%94%E7%9A%84%E8%AF%9D.......assets/v2-2ba61e715919d5ab02a521c55f512b93_1440w.webp)

参考项目地址：[https://github.com/mckaywrigley/paul-graham-gpt](https://github.com/mckaywrigley/paul-graham-gpt)

[https://github.com/mckaywrigley/paul-graham-gpt​github.com/mckaywrigley/paul-graham-gpt](https://link.zhihu.com/?target=https%3A//github.com/mckaywrigley/paul-graham-gpt)

[GitHub - mckaywrigley/paul-graham-gpt: AI search & chat for all of Paul Graham’s essays.](https://link.zhihu.com/?target=https%3A//github.com/mckaywrigley/paul-graham-gpt)

[https://github.com/mckaywrigley/paul-graham-gpt​github.com/mckaywrigley/paul-graham-gpt](https://link.zhihu.com/?target=https%3A//github.com/mckaywrigley/paul-graham-gpt)

![v2-d07832a1d6414f41748986bb64932500_180x120.png](%E6%83%B3%E8%87%AA%E5%B7%B1%E5%88%A9%E7%94%A8OpenAI%E5%81%9A%E4%B8%80%E4%B8%AA%E6%96%87%E6%A1%A3%E9%97%AE%E7%AD%94%E7%9A%84%E8%AF%9D.......assets/v2-d07832a1d6414f41748986bb64932500_180x120.png)

[利用ChatGPT 和Milvus快速搭建智能问答机器人​www.cnblogs.com/shanyou/p/17179348.html](https://link.zhihu.com/?target=https%3A//www.cnblogs.com/shanyou/p/17179348.html)

---

## 3 llama-index(gpt-index)对话式文档问答解决方案

本篇介绍了类似CHATPDF这类应用的背后大致运作原理。

### 3.1 任务描述和问题分析

对话式文档问答，字面意思就是基于文档建立的问答系统。使用这项技术，开发者无需梳理意图、词槽，无需进行问题和答案的整理，只需准备文本格式的业务文档（例如洗碗机的使用手册），就可以得到一个问答系统，回答用户的各种问题（例如“洗碗机排水管堵塞了怎么办“）。

如果使用openai api来实现对话式文档问答，最朴素的想法把这个当成一个阅读理解问题，构建如下的prompt：

- 现有一个问题：“洗碗机排水管堵塞了怎么办”，请根据下面的文章来回答，文章内容如下："......"

这种方法在文档较长时存在两个问题：

- 第一，openai api存在最大长度的限制，例如chatgpt的最大token数为4096，此时直接对文档截断，存在上下文丢失的问题
- 第二，api的调用费用和token长度成正比，tokens数太大，则每次调用的成本都会很高

### 3.2 解决思路

可以参考搜索引擎中“先检索再重排”的思路，针对文档问答设计“先检索再整合“的方案，整体思路如下：

- 首先准备好文档，并整理为纯文本的格式。把每个文档切成若干个小的chunks
- 调用文本转向量的接口，将每个chunk转为一个向量，并存入向量数据库
- 文本转向量可以使用openai embedding（[https://platform.openai.com/docs/guides/embeddings/what-are-embeddings](https://link.zhihu.com/?target=https%3A//platform.openai.com/docs/guides/embeddings/what-are-embeddings)）
- 也可以使用其他方案，如fasttext/simbert等
- 当用户发来一个问题的时候，将问题同样转为向量，并检索向量数据库，得到相关性最高的一个或几个chunk
- 将问题和chunk合并重写为一个新的请求发给openai api，可能的请求格式如下：

```other
结合下面的段落来回答问题：“ 如何使用预约功能”

* 段落1: 您可以按照以下步骤使用预约功能....
* 段落2: 在使用预约功能之前，请确保您已正确地设置了洗涤程序....
* 段落3: .......
```

上述“先检索再整合的逻辑”已经封装在llama-index库中

### 3.3 代码案例

llama-index的前身是gpt-index项目，最近才刚改名为'llama-index'。下面给出一个基于llama-index实现文档问答的具体demo，代码已上传至github:

[https://github.com/xinsblog/try-llama-index​github.com/xinsblog/try-llama-index](https://link.zhihu.com/?target=https%3A//github.com/xinsblog/try-llama-index)

一些教程案例：

[https://uxdesign.cc/i-built-an-ai-that-answers-questions-based-on-my-user-research-data-7207b052e21c​uxdesign.cc/i-built-an-ai-that-answers-questions-based-on-my-user-research-data-7207b052e21c](https://link.zhihu.com/?target=https%3A//uxdesign.cc/i-built-an-ai-that-answers-questions-based-on-my-user-research-data-7207b052e21c)

参考材料：

[Welcome to LlamaIndex (GPT Index)!​gpt-index.readthedocs.io/en/latest/index.html](https://link.zhihu.com/?target=https%3A//gpt-index.readthedocs.io/en/latest/index.html)

[严昕：llama-index(gpt-index)：后chatgpt时代的对话式文档问答解决方案161 赞同 · 54 评论文章](https://zhuanlan.zhihu.com/p/613155165)

---

## 4 loli.xing **基于 ChatGPT 的客服系统**

在 OpenAI 放出 gpt-3.5-turbo 模型之后,我们决定使用 AI 来加速目前我们重复率最高的工作:客服

按照以下方法来实现:

- 使用[语雀的 API](https://link.zhihu.com/?target=https%3A//www.yuque.com/yuque/developer) 获取我们的帮助手册及FAQ
- 获得到每篇文章后,按照 markdown 的标题进行分割,每个小标题对应一块语料.并在数据库中记录对应的网址和锚点,方便后续输出时同步给出参考文档.
- 使用 [openai embeddings](https://link.zhihu.com/?target=https%3A//platform.openai.com/docs/guides/embeddings/embeddings) 获取每块语料的向量表示.
- 对用户的提问也使用 openai embeddings 提取向量.
- 使用 余弦相似度 计算用户提问和每块语料的相似度,并返回相似度最高10块的语料.
- 对每块语料按照相似度从高到低的顺序 对 token 进行求和,获取小于 2000 时的语料列表.
- 按照以下格式给与 gpt-3.5-turbo 的 system role 输入

```other
你是 $$$ 系统的客服,请按照后续给予的使用手册回答用户的问题.
 使用手册内容如下:
```

- 获取 gpt-3.5-turbo 的输出.

目前处于安全考虑, gpt-3.5-turbo 的输出仅发送到客服汇总群,并由客服人员进行回复.同时给与客服相关语料的标题及链接,方便客服人员进行回复.

[基于 ChatGPT 的客服系统​loli.xing.moe/ChatGPT_as_customer_service/](https://link.zhihu.com/?target=https%3A//loli.xing.moe/ChatGPT_as_customer_service/)

---

## 5 Document_QA

[Document_QA​github.com/fierceX/Document_QA](https://link.zhihu.com/?target=https%3A//github.com/fierceX/Document_QA)

根据传入的文本文件，回答你的问题。

读取文件，并进行分割

- 对于每段文本，使用text-embedding-ada-002生成特征向量
- 将向量和文本对应关系存入本地pkl文件
- 对于用户输入，生成向量
- 使用向量数据库进行最近邻搜索，返回最相似的文本列表
- 使用gpt3.5的chatAPI，设计prompt，使其基于最相似的文本列表进行回答

就是先把大量文本中提取相关内容，再进行回答，最终可以达到类似突破token限制的效果

后续可以考虑将openai的文本向量改成自定义的向量生成工具

---

## 6 ChatWeb

> ChatWeb可以爬取任意网页并提取正文，生成概要，然后根据正文内容回答你的问题。 目前是个原理展示的Demo，还没有细分逻辑。 基于gpt3.5的chatAPI和embeddingAPI，配合向量数据库。 [https://github.com/SkywalkerDarren/chatWeb​github.com/SkywalkerDarren/chatWeb](https://link.zhihu.com/?target=https%3A//github.com/SkywalkerDarren/chatWeb) 基本类似于现有的chatPDF，自动化客服AI等项目的原理。

- 爬取网页
- 提取正文
- 对于每一段落，使用gpt3.5的embeddingAPI生成向量
- 每一段落的向量和全文向量做计算，生成概要
- 将向量和文本对应关系存入向量数据库
- 对于用户输入，生成向量
- 使用向量数据库进行最近邻搜索，返回最相似的文本列表
- 使用gpt3.5的chatAPI，设计prompt，使其基于最相似的文本列表进行回答

就是先把大量文本中提取相关内容，再进行回答，最终可以达到类似突破token限制的效果

## 7 chatpdf-minimal-demo

[https://github.com/postor/chatpdf-minimal-demo​github.com/postor/chatpdf-minimal-demo](https://link.zhihu.com/?target=https%3A//github.com/postor/chatpdf-minimal-demo)

![v2-9079066fd52d797cb222d8ae8551d34a_1440w.webp](%E6%83%B3%E8%87%AA%E5%B7%B1%E5%88%A9%E7%94%A8OpenAI%E5%81%9A%E4%B8%80%E4%B8%AA%E6%96%87%E6%A1%A3%E9%97%AE%E7%AD%94%E7%9A%84%E8%AF%9D.......assets/v2-9079066fd52d797cb222d8ae8551d34a_1440w.webp)

实现原理 | process flow

- 文章切片到段落 | split articles into pieces
- 通过 OpenAI 的 embedding 接口将每个段落转换为 embedding | convert each piece into embedding with OpenAI
- 将提问的问题转换为 embedding | convert user question into embedding
- 把问题的 embedding 比较所有段落 embedding 得到近似程度并排序 | compare question embedding with all the embeddings of pieces and sort the result
- 把和提问(语义)最接近的一个或几个段落作为上下文，通过 OpenAI 的对话接口得到最终的答案 | use the nearest (meaning) piece(s) as context and ask ChatGPT for the final answer

几个核心代码片段：

获取embedding：

```other
import openai

def get_embedding(text: str, model: str=EMBEDDING_MODEL) -> list[float]:
    result = openai.Embedding.create(
      model=model,
      input=text
    )
    return result["data"][0]["embedding"]
```

用户问题排序：

```other
def order_document_sections_by_query_similarity(query: str, embeddings) -> list[(float, (str, str))]:
    #pprint.pprint("embeddings")
    #pprint.pprint(embeddings)
    """
    Find the query embedding for the supplied query, and compare it against all of the pre-calculated document embeddings
    to find the most relevant sections. 
    
    Return the list of document sections, sorted by relevance in descending order.
    """
    query_embedding = get_embedding(query)
    
    document_similarities = sorted([
        (vector_similarity(query_embedding, doc_embedding), doc_index) for doc_index, doc_embedding in enumerate(embeddings)
    ], reverse=True, key=lambda x: x[0])
    
    return document_similarities
```

当问题被问到时，获取最近的信息作为上下文并询问 ChatGPT:

```other
def ask(question:str,embeddings,sources):
    ordered_candidates = order_document_sections_by_query_similarity(question,embeddings)
    ctx = ""
    for candi in ordered_candidates:
        next = ctx + " " + sources[candi[1]]
        if len(next)>CONTEXT_TOKEN_LIMIT:
            break
        ctx = next
    if len(ctx) == 0:
      return ""    
    
    prompt = "".join([
        u"Answer the question based on the following context:

"
        u"context:"+ ctx +u"

"
        u"Q:"+question+u"

"
        u"A:"
                        ])

    completion = openai.ChatCompletion.create(model="gpt-3.5-turbo", messages=[{"role": "user", "content":prompt}])
    return [prompt, completion.choices[0].message.content]
```

一个网页版图例：

![v2-369077b2ea7cbf9f3f17d37a46d71ddc_1440w.webp](%E6%83%B3%E8%87%AA%E5%B7%B1%E5%88%A9%E7%94%A8OpenAI%E5%81%9A%E4%B8%80%E4%B8%AA%E6%96%87%E6%A1%A3%E9%97%AE%E7%AD%94%E7%9A%84%E8%AF%9D.......assets/v2-369077b2ea7cbf9f3f17d37a46d71ddc_1440w.webp)

screenshot of postor/chatpdf-minimal-demo

[https://postor.medium.com/how-to-code-a-project-like-chatpdf-e40441cb4168​postor.medium.com/how-to-code-a-project-like-chatpdf-e40441cb4168](https://link.zhihu.com/?target=https%3A//postor.medium.com/how-to-code-a-project-like-chatpdf-e40441cb4168)

编辑于 2023-03-16 00:09・IP 属地上海