# transformer架构的核心公式其实类似于数学期望，理解起来也不复杂，但为什么这个模型这么强呢？

链接：[https://www.zhihu.com/question/580810624/answer/2975158438](https://www.zhihu.com/question/580810624/answer/2975158438)

需要知道[离散网络](https://www.zhihu.com/search?q=%E7%A6%BB%E6%95%A3%E7%BD%91%E7%BB%9C&search_source=Entity&hybrid_search_source=Entity&hybrid_search_extra=%7B%22sourceType%22%3A%22answer%22%2C%22sourceId%22%3A2975158438%7D)结构的可能性量级是超越人们的想象的。
一般人们认为n元素系统的全部联系是n！量级，也就是完全图，但实际上，n元素系统的可能[幂集代数](https://www.zhihu.com/search?q=%E5%B9%82%E9%9B%86%E4%BB%A3%E6%95%B0&search_source=Entity&hybrid_search_source=Entity&hybrid_search_extra=%7B%22sourceType%22%3A%22answer%22%2C%22sourceId%22%3A2975158438%7D)结构是2↑2↑n，是双指数级，可想而知图能表达的信息会有多丰富。
5→e9
10→e308
12→e1233
幂集代数可能太过一般了，增长速度快的惊人，而且越来越快。n元素系统可能具有的[二元运算](https://www.zhihu.com/search?q=%E4%BA%8C%E5%85%83%E8%BF%90%E7%AE%97&search_source=Entity&hybrid_search_source=Entity&hybrid_search_extra=%7B%22sourceType%22%3A%22answer%22%2C%22sourceId%22%3A2975158438%7D)结构数目为n↑(n*n)，不够直观，代入几个数字就明白了，
5→e17
10→e100,几乎相当于人们推测的宇宙中所有的粒子数
20→e520,这个数字远远超越人们的理解能力
因此，数目很小的[离散系统](https://www.zhihu.com/search?q=%E7%A6%BB%E6%95%A3%E7%B3%BB%E7%BB%9F&search_source=Entity&hybrid_search_source=Entity&hybrid_search_extra=%7B%22sourceType%22%3A%22answer%22%2C%22sourceId%22%3A2975158438%7D)，可以表示的状态数是远远超越人们的想象的。如此大的[状态空间](https://www.zhihu.com/search?q=%E7%8A%B6%E6%80%81%E7%A9%BA%E9%97%B4&search_source=Entity&hybrid_search_source=Entity&hybrid_search_extra=%7B%22sourceType%22%3A%22answer%22%2C%22sourceId%22%3A2975158438%7D)，宣称他能完全模拟人的大脑都不会让人意外。
人的大脑缺点很多，想要快速提高智能不太现实。原因就在于人的大脑神经元连接是稳定的，权重与激励想要变化很困难，而且极其痛苦，毕竟学一会，就觉得大脑累了。
而AI不知疲倦，而且可塑性极强，相比于人类的大脑，接受新事物新知识的能力自然是更加优越。更应该奇怪的是为什么之前的人工智能表现不出这种强大的能力。可能说明了特定的连接结构才能发挥出这种作用，也就是现在使用的[transform](https://www.zhihu.com/search?q=transform&search_source=Entity&hybrid_search_source=Entity&hybrid_search_extra=%7B%22sourceType%22%3A%22answer%22%2C%22sourceId%22%3A2975158438%7D)，似乎把握住了某种本质。而且也揭示了大模型小型化的潜力。不过，目前这种结构恐怕难以做到小型化，因为很多问题没有理解清楚。
知识是具有结构的，没有结构的信息只是破碎的片段。需要找到知识的一般结构，以及这些结构的转换规律以及[代数闭包](https://www.zhihu.com/search?q=%E4%BB%A3%E6%95%B0%E9%97%AD%E5%8C%85&search_source=Entity&hybrid_search_source=Entity&hybrid_search_extra=%7B%22sourceType%22%3A%22answer%22%2C%22sourceId%22%3A2975158438%7D)，然后研究出这种代数闭包的本质表示，这就是可理解的人工智能。
但是，具体会如何表现还是需要不同的语料喂养，就像人类在不同的环境下成长，大脑与思维也会很不同。

看了其他的回答后，我发现，这一轮的AI革命是整体观点的胜利，以往的AI模型是由点到面的序列式传播，所以速度，精度和深度受到了极大限制，现在的AI模型通过并行化提高速度，通过[长期记忆机制](https://www.zhihu.com/search?q=%E9%95%BF%E6%9C%9F%E8%AE%B0%E5%BF%86%E6%9C%BA%E5%88%B6&search_source=Entity&hybrid_search_source=Entity&hybrid_search_extra=%7B%22sourceType%22%3A%22answer%22%2C%22sourceId%22%3A2975158438%7D)提高迭代深度，而速度和深度的提高带来精度的极大改善。和图观点不谋而合，子图计算对应于多注意力与并行化处理，而结果综合对应于记忆与选择机制。再加上时间演化图理论，整体构成了一个动态的，一心多用的，具备记忆与选择能力的智能。

这也说明了中心与去中心的结合，7输出肯定是中心化的，综合考虑所有因素，而思考是去中心化的，每一个模块给出自己的判断。记忆也很关键，维持判断的一致性。

不愧是最先进的技术成果。