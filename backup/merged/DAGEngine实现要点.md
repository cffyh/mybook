# DAGEngine实现要点

1、参数传递

![Image.tiff](DAGEngine%E5%AE%9E%E7%8E%B0%E8%A6%81%E7%82%B9.assets/Image.tiff)

![Image (2).tiff](DAGEngine%E5%AE%9E%E7%8E%B0%E8%A6%81%E7%82%B9.assets/Image%20(2).tiff)

输入List可以将context和上游的输出传递给下游，而且不需要配置。

2、配置

- dag描述和operator参数可以解耦；

[dag.json](DAGEngine%E5%AE%9E%E7%8E%B0%E8%A6%81%E7%82%B9.assets/dag.json)

- operator参数
    - Spring Boot yml 文件读取：@ConfigurationProperties 、@EnableConfigurationProperties、@Value、Environment
    - nacos config。 data-id
        - 一个应用一个data-id。
        - 因为更新会重新init bean，可能会失败。 手动写代码监听也是有必要的

3、并行异步执行

- 没有上游节点，就能成为start节点
- 没有下游节点就能成为
- 入度控制

4、执行异常

- 超时控制