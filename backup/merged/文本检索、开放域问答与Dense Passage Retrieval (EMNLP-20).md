# 文本检索、开放域问答与Dense Passage Retrieval (EMNLP-20)

发布于2022-03-28 18:31:35阅读 4740

![b777f802ab215bb48d6ea748727e2a48.png](%E6%96%87%E6%9C%AC%E6%A3%80%E7%B4%A2%E3%80%81%E5%BC%80%E6%94%BE%E5%9F%9F%E9%97%AE%E7%AD%94%E4%B8%8EDense%20Passage%20Retrieval%20(EMNLP-20).assets/b777f802ab215bb48d6ea748727e2a48.png)

- 标题：Dense Passage Retrieval for Open-Domain Question Answering
- 会议：EMNLP-20
- 机构：Facebook AI, University of Washington, Princeton University
- 链接：[https://readpaper.com/paper/3099700870](https://readpaper.com/paper/3099700870)

> **一句话总结：** 一个很好的文本检索（IR）、问答（QA）的学习材料。开放域问答一般分两步——检索和阅读理解，本文提出的DPR是一个高效的基于语义匹配的检索模型，从而提高整体QA的效果，该思路对后续的**对比学习**的一系列工作都有启发。

## **Open-domain question answering (QA)**

QA可以分为Close-domain QA和Open-domain QA，前者一般限制在某个特定领域，有一个给定的该领域的知识库，比如医院里的问答机器人，只负责回答医疗相关问题，甚至只负责回答该医院的一些说明性问题，再比如我们在淘宝上的[智能客服](https://cloud.tencent.com/product/icr?from=20065&from_column=20065)，甚至只能在它给定的一个问题集合里面问问题；而Open-domain QA则是我们可以问任何事实性问题，一般是给你一个海量文本的语料库，比方Wikipedia/百度百科，让你从这个里面去找回答任意非主观问题的答案，这显然就困难地多。总结一下，Open-domain QA的定义：

![4dea709b3fed3cb6f74b1840dbf173fa.png](%E6%96%87%E6%9C%AC%E6%A3%80%E7%B4%A2%E3%80%81%E5%BC%80%E6%94%BE%E5%9F%9F%E9%97%AE%E7%AD%94%E4%B8%8EDense%20Passage%20Retrieval%20(EMNLP-20).assets/4dea709b3fed3cb6f74b1840dbf173fa.png)

![a58d5ce1e611ba1ed4fa9834eb279c73.png](%E6%96%87%E6%9C%AC%E6%A3%80%E7%B4%A2%E3%80%81%E5%BC%80%E6%94%BE%E5%9F%9F%E9%97%AE%E7%AD%94%E4%B8%8EDense%20Passage%20Retrieval%20(EMNLP-20).assets/a58d5ce1e611ba1ed4fa9834eb279c73.png)

> Open-domain QA，是这样一种任务：给定海量文档，来回答一个事实性问题（factoid questions ）。
注意，是回答factoid questions，即一个很客观的问题，不能问一些主观的问题。
这就类似于我们只在在搜索引擎里搜索某个问题的答案，我们希望搜索引擎能直接告诉我们答案，而不单单是找到一篇文章，然后我们需要自己找答案。
举个例子，正好我前几天搜索triplet loss的时候印象深刻：
我在Google里面直接搜triplet loss：

image-20220216105121926

首先，排在第一的结果就是Wikipedia的link，同时上面显示了一段话，让我不用点开Wikipedia，就能直接知道triplet loss**是什么，有什么用**，另外，仔细看的话，发现它把具体定义的那句话给我加粗了，就是我上面高亮的部分。

如果我继续点击进入Wikipedia，会更清楚的看到搜索引擎帮我把我想要的答案给高亮了（下图中的紫色部分是浏览器自动显示的，不是我选择的）：

image-20220216104917986

我想这就是个很好的例子，告诉我们open-domain QA想要做的是什么事。

当然，搜索引擎返回答案，还涉及到其他技术，比如有一些事实性问题，比如“姚明比奥尼尔高多少”，就需要借助[知识图谱](https://cloud.tencent.com/product/tkg?from=20065&from_column=20065)等技术来实现了。

### **Open-domain QA的两个步骤**

我们这里讲深度学习时代的Open-domain QA，传统的方法往往涉及到十分复杂的组件，而随着基于深度学习的阅读理解（reading comprehension）模型的兴起，我们现在可以把Open-domain QA给简化成两个步骤：文本检索与阅读理解。

**① 文本检索**：需要一个retriever，从海量文本中，找到跟question最相关的N篇文档，这些文档中包含了该问题的答案；

**② 阅读理解**：需要一个reader，从上面抽取出来的文档中，找到具体答案。

### **文本检索**

对于文本的检索，目前最常用的方案就是基于**倒排索引（inverted index）**的关键词检索方式，例如最常用的ElasticSearch方案，就是基于倒排索引的，简言之，这是一种关键词搜索，具体的匹配排序规则有TF-IDF和BM25两种方式。这种文本检索的方式，是一种文本的bag-of-words表示，通过词频、逆文档频率等统计指标来计算question和document之间的相关性，可参考BM25的wiki。

![335ed156c83c1c87d664b9bbdf08d844.png](%E6%96%87%E6%9C%AC%E6%A3%80%E7%B4%A2%E3%80%81%E5%BC%80%E6%94%BE%E5%9F%9F%E9%97%AE%E7%AD%94%E4%B8%8EDense%20Passage%20Retrieval%20(EMNLP-20).assets/335ed156c83c1c87d664b9bbdf08d844.png)

这种方式，是比较“硬”的匹配，当你搜索的关键词准确、明确时，搜索结果会非常好，但是当你只知道大概意思，搜索的结果可能就很差，因为bag-of-words的表示，无法认识到词语之间的相似性关系，因此就只能搜索到你输入的关键词，却无法找到词语不同但意思相近的结果。

一般的Open-domain QA都会直接使用这种基于TF-IDF或者BM25的匹配方式来进行检索，本论文则是提出，我们可以使用语义的匹配来达到更好的效果，弥补硬匹配的不足，这也是本论文的主要关注点。具体地，我们可以训练一个语义表示模型，赋予文本一个dense encoding，然后通过向量相似度来对文档进行排序。

其实向量搜索也很常见了，像以图搜图就是典型的向量相似度搜索，常用的开源引擎有Facebook家的FAISS.

![6e509ef648fae2905a05a9f4f32f220d.png](%E6%96%87%E6%9C%AC%E6%A3%80%E7%B4%A2%E3%80%81%E5%BC%80%E6%94%BE%E5%9F%9F%E9%97%AE%E7%AD%94%E4%B8%8EDense%20Passage%20Retrieval%20(EMNLP-20).assets/6e509ef648fae2905a05a9f4f32f220d.png)

### **阅读理解**

阅读理解一般指的是，给定一个问题（question）和一段话（passage），要求从这段话中找出问题的答案。训练方式一般是我们计算passage中每个token是question的开头s或者结尾t的概率，然后计算正确答案对应start/end token最大似然损失之和。具体咱们可以参考BERT论文中对fine-tuning QA模型中的方法介绍：

![868dd92774794609294412a2b980bec3.png](%E6%96%87%E6%9C%AC%E6%A3%80%E7%B4%A2%E3%80%81%E5%BC%80%E6%94%BE%E5%9F%9F%E9%97%AE%E7%AD%94%E4%B8%8EDense%20Passage%20Retrieval%20(EMNLP-20).assets/868dd92774794609294412a2b980bec3.png)

源自BERT论文

即，通过BERT encoder，我们可以得到每个token的一个representation，然后我们再额外设置一个start vector和一个end vector，与每个token的representation计算内积，再通过softmax归一化，就得到了每个token是start或者end的概率。

我在一个博客上看到了一个画的更清楚的图：

![6e82b9333b447f4dd652da916624d880.png](%E6%96%87%E6%9C%AC%E6%A3%80%E7%B4%A2%E3%80%81%E5%BC%80%E6%94%BE%E5%9F%9F%E9%97%AE%E7%AD%94%E4%B8%8EDense%20Passage%20Retrieval%20(EMNLP-20).assets/6e82b9333b447f4dd652da916624d880.png)

[https://mccormickml.com/2020/03/10/question-answering-with-a-fine-tuned-BERT/#part-1-how-bert-is-applied-to-question-answering](https://mccormickml.com/2020/03/10/question-answering-with-a-fine-tuned-BERT/#part-1-how-bert-is-applied-to-question-answering)

关于阅读理解的具体内容，这里也不赘述，这也不是今天这篇论文的重点。

## **Dense Passage Retriever (DPR)**

本文最重要的就是这个DPR了，它解决的就是open-domain QA中的检索问题，目标是训练一个文本表示模型，可以对question和passage进行很好的语义向量表示，从而实现高精度的向量搜索。

DPR是一个retriever，实际上分两块，首先我们需要得到文档的向量表示，然后我们需要一个向量搜索工具，后者本文中直接使用著名的FAISS向量搜索引擎，所以重点就是训练一个文本表示模型。

### **Dual-encoder**

本文使用了一个dual-encoder的框架，可以理解为一个双塔结构，一个encoder EP(⋅) 专门对passage进行表示，另一个encoder EQ(⋅) 专门对question进行表示，然后我们使用内积来表示二者的相似度：

sim(p,q)=EP(p)⋅EQ(q)

### **损失函数设计**

我们首先构造训练样本，它是这样的形式：

```math
\\
D = {}_i

```

即，**每个训练样本，都是由1个question，1个positive passage和n个negative passage构成的**。positive就是与问题相关的文本，negative就是无关的文本。

用一个样本中每个passage（n+1个）和当前question的相似度作为logits，使用softmax对logits进行归一化，就可以得到每个passage与当前question匹配的概率，由此就可以设计极大似然损失——取positive passage的概率的负对数：

L(q,p+,p−1,...,p−n)=−logexp(sim(q,p+))exp(sim(q,p+))+∑nj=1exp(sim(q,p−j))

上面的公式里，为方便看清楚，我省去了样本的下标i 。可以看到，这就相当于一个cross-entropy loss。而这样的设计，跟现在遍地的对比学习的loss非常像，例如知名的SimCSE也引用了本文：

![ad98ed0b046e89b09ba87357aba25b47.png](%E6%96%87%E6%9C%AC%E6%A3%80%E7%B4%A2%E3%80%81%E5%BC%80%E6%94%BE%E5%9F%9F%E9%97%AE%E7%AD%94%E4%B8%8EDense%20Passage%20Retrieval%20(EMNLP-20).assets/ad98ed0b046e89b09ba87357aba25b47.png)

### **负样本选择**

在上面的损失函数中，我们发现负样本起着重要的作用。另外，正样本一般都是确定的，而负样本的选择则是多种多样的，所以负样本怎么选，对结果应该有很大的影响。

作者设计了三种负样本（negative passage）选择的方式：

1. **Random**：从语料库中随机抽取一个passage，基本上都是跟当前question无关的；
2. **BM25**：使用基于BM25的文本检索方式在语料库中检索跟question最相关的文本，但要求不包含答案；
3. **Gold**：在训练样本中，其他样本中的positive passage。即对于训练样本i 和j ，qi 对应的正样本是p+i ，而这个p+i 可以作为qj 的负样本。

既然都命名为Gold了，那说明作者对它给予了厚望，肯定是主要的负样本来源。

论文最终的最佳实践，就是主要采用同一个mini-batch中的Gold passages，配合上一个BM25 passage（以及同batch内其他question的BM25）。

### **关键的Trick——In-batch negatives**

假设我们的batch size为B，每个question有1个positive和n个negative，那么一个batch内就有B×(n+1) 个passages要经过encoding，而一般我们都需要比较多的negatives才能保证较好的效果，所以光是encoding，这个计算开销就很大。

于是，有人就想出了一个办法，我们只需要B个questions和其对应的B个positives，形成两个矩阵Q 和P ，然后“我的positive，可以当做你的negative”，这样我们就不需要额外再找negative了，然后直接算一个S=QPT 就可以得到计算损失函数所需要的所有pair的相似度，这就使得整个过程变得高效又简洁。由于不需要额外找negatives，所以一个batch内只有B 个positive passages需要经过encoding，这比前面的方法减少了n+1倍，干净又卫生啊兄弟们。

上面说的方式，相当于只使用Gold负样本，实际上作者在最佳方案中还使用了BM25负样本，但也是采用的in-batch training的策略，即，我每个question都找一个BM25负样本， 然后，该BM25样本也会作为同batch内所有其他question的负样本，这相当于再增加一个矩阵M ，总共有B×2 个passages进行encoding，然后多计算一个矩阵乘法得到相似度。

最后注意，in-batch training并不是DPR论文首创，前面很多工作中已经得到成功应用。

## **实验设置&数据集**

### **Knowledge Source**

知识库，就是我们open-domain QA使用什么语料库来进行问答。本文选用Wikipedia，这也是最常用的设定。当然，Wikipedia是一篇篇文章，通常是十分长，模型不便处理，因此这里作者将所有文本，都继续划分成100个词长度的passages，这些length=100的passages就是本文做检索的基本单元。另外，每个passage还在开头拼接上了对应Wikipedia page的title。

### **QA Datasets**

我们还需要有<问题，答案>这样的数据集，来让我们训练retriever和reader。

具体数据集有：

- Natural Questions (NQ) ：提供了question和answer，且答案全都来自Wikipedia
- TriviaQA：提供question-answer-evidence triples
- WebQuestions (WQ)：只提供了question和answer
- CuratedTREC (TREC)：只提供了question和answer
- SQuAD v1.1：提供question，context和answer

这些数据集中，对于TriviaQA，WQ和TREC，由于没有给相关的context，没法直接那answer当做positive passages，所以作者选择在Wikipedia passages中使用BM25来检索包含answer的passage来作为positive passage（虽然这种做法我感觉不一定好，因为匹配上的，不一定就能回答你的问题，比如你问“阿里巴巴谁创办的”，答案是“马云”，但包含“马云”的句子可能是“马云在达沃斯论坛演讲”，这显然不能回答该问题）。

对于SQuAD和NQ，由于这些数据集提供的passage跟作者自己的预处理方式不一样，所以作者用这些passage在前面对Wikipedia预处理后的passages pool中去匹配得到positive passage。

### **Baselines**

对于retrieval任务，baseline就是BM25算法，同时作者还对比了BM25+DPR的效果，即将二者的得分进行加权平均:

BM25(q,p)+λ⋅sim(q,p)

，其中作者发现λ=1.1 效果较好。

另外对于DPR来说，越多的训练样本肯定越好，所以除了在单个数据集上训练测试外，作者还尝试了使用所有数据集的训练样本来训练DPR然后测试。而BM25也是纯统计方法，所以不存在使用训练数据一说。

## **Retrieval任务实验结果**

### **Main Results：**

结果见下表：

![264fdf97c56b5cd55dfd6bec190b8908.png](%E6%96%87%E6%9C%AC%E6%A3%80%E7%B4%A2%E3%80%81%E5%BC%80%E6%94%BE%E5%9F%9F%E9%97%AE%E7%AD%94%E4%B8%8EDense%20Passage%20Retrieval%20(EMNLP-20).assets/264fdf97c56b5cd55dfd6bec190b8908.png)

retrieval任务结果

可以发现，**除了SQuAD数据集**，其他的数据集上，DPR的表现都不错，都大幅超越了BM25算法，而结不结合BM25，其实影响不是很大，但使用更多的训练数据集，总体上肯定更好些。

### **在精确匹配上效果并不好：**

**在SQuAD上，效果很差，这一点很有意思**。关于这一点，作者给出的解释是：

![b9c9b753cc46e3436bcc0e16a4519695.png](%E6%96%87%E6%9C%AC%E6%A3%80%E7%B4%A2%E3%80%81%E5%BC%80%E6%94%BE%E5%9F%9F%E9%97%AE%E7%AD%94%E4%B8%8EDense%20Passage%20Retrieval%20(EMNLP-20).assets/b9c9b753cc46e3436bcc0e16a4519695.png)

image-20220218192133247

即 1.这个数据集的question跟passage再语言上高度重合，所以BM25天然有优势；2. 这个数据集采样是有偏的。

其实这也告诉我们，你DPR也不是万能的，天下没有免费的午餐，在那种“精确匹配”的场景下，相似度搜索一般不会比bag-of-words硬匹配更好。

### **训练好的DPR需要多少数据量：**

然后我们看看使用多少数据量，DPR就超过了BM25：

![113864b91a917f4dd015d08e46046ac0.png](%E6%96%87%E6%9C%AC%E6%A3%80%E7%B4%A2%E3%80%81%E5%BC%80%E6%94%BE%E5%9F%9F%E9%97%AE%E7%AD%94%E4%B8%8EDense%20Passage%20Retrieval%20(EMNLP-20).assets/113864b91a917f4dd015d08e46046ac0.png)

可见，仅仅使用1k的数据量，DPR这种语义匹配的方式，就超越了BM25这种硬匹配。

### **In-batch negatives：**

然后再看看negative样本的选择的影响，也看看in-batch training这种方式怎么样：

![520121a0b92da4bbf80197b6f1041911.png](%E6%96%87%E6%9C%AC%E6%A3%80%E7%B4%A2%E3%80%81%E5%BC%80%E6%94%BE%E5%9F%9F%E9%97%AE%E7%AD%94%E4%B8%8EDense%20Passage%20Retrieval%20(EMNLP-20).assets/520121a0b92da4bbf80197b6f1041911.png)

in-batch training

这个表初次读的时候一直搞不懂，文中也没写明白，后来请教了同学才搞明白：

第一个block，batch size不太清楚，有可能是128，但不使用in-batch的策略，每个question都自带7个negatives参与训练。这个block是为了对比不同的negative的效果，发现其实差不多，各有优劣。

第二个block，batch size分别是8，32，128，采用的in-batch策略，使用同batch内的其他positive作为negative，所以batch越大，可以使用的negatives就越多，因此效果就越好，效果比第一个block好了很多。

第三个block，batch size分别是32，32，128，除了Gold，每个样本还带了1-2个BM25样本，且这些样本在整个batch内共享（参考上文中“负样本选择”一节的介绍），发现，带一个BM25样本就有明显提高，再多了就没效果了。

总之，这个实验说明，in-batch training是很高效、有效的一种方法，然后负样本我们可以主要使用batch内的那些positives（即Gold passages），再配上一个额外的BM25 passage即可取得很好的效果。

### **Similarity和loss的选择**

本文采用的是dot product作为相似度度量，作者还测试了L2距离和cosine similarity，发现最差的是cosine similarity。（这一点有意思，可探究一下为什么）

关于loss，除了本文的NLL loss，作者还尝试了在similarity任务中常用的triplet loss，发现效果差别不大，但还是NLL loss更好一点。

### **Cross-dataset generalization**

这里文中也是一笔带过，所以我也不赘述，我只是很高兴在论文中看到了这样的实验，cross-dataset generalization是大多数人不会去考虑的一个实验，但对于验证泛化性能是很重要的。

## **End-to-End QA实验结果**

这部分并不是本文的重点，前面讲了，除了训练一个retriever（对应本文的DPR），完成open-domain QA还需要一个reader。之前的sota工作都涉及到复杂的预训练，但是本文重点在于搞一个很好的retriever——DPR，从而只需要简单训练一个reader就够了，下面是实验结果：

![bddebac900c1014f42ef8aadb2eb3ff1.png](%E6%96%87%E6%9C%AC%E6%A3%80%E7%B4%A2%E3%80%81%E5%BC%80%E6%94%BE%E5%9F%9F%E9%97%AE%E7%AD%94%E4%B8%8EDense%20Passage%20Retrieval%20(EMNLP-20).assets/bddebac900c1014f42ef8aadb2eb3ff1.png)

QA实验

最后再贴一段作者自己的评论：

![66b157793b2ded42d84d29c2a0ddfbe7.png](%E6%96%87%E6%9C%AC%E6%A3%80%E7%B4%A2%E3%80%81%E5%BC%80%E6%94%BE%E5%9F%9F%E9%97%AE%E7%AD%94%E4%B8%8EDense%20Passage%20Retrieval%20(EMNLP-20).assets/66b157793b2ded42d84d29c2a0ddfbe7.png)

## **总结**

这篇文章最大的亮点在于在训练学习text representation的时候如何选择negative samples，其中的Gold和BM25对学习一个好的表示起到了重要的作用，因此仅仅使用1k个训练样本，就可以训练一个超越BM25算法的文本检索工具。本文也为后续的一些对比学习工作，例如SimCSE等产生了启发，作为文本相似度匹配的重要工作，本文还是很值得一读的。

以上，这篇文章就解读完毕了，其实我之前怎么了解过QA，而本文对于QA小白来说也是一个绝佳的教材，所以这篇文章除了让我了解DPR这个工作之外，也让我学习了很多关于QA的相关知识，收获颇丰。

推荐资料：

[1]Wikipedia: Question Answering [https://en.wikipedia.org/wiki/Question_answering](https://en.wikipedia.org/wiki/Question_answering) [2]Wikipedia: BM25 [https://en.wikipedia.org/wiki/Okapi_BM25](https://en.wikipedia.org/wiki/Okapi_BM25) [3] DrQA: Reading Wikipedia to Answer Open-Domain Questions [4] Efficient Natural Language Response Suggestionfor Smart Reply

最后，特别感谢MSRA张航同学给予的答疑，解决了本文理解上的几个关键问题 **：）**