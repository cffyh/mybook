# 控制理论（control theory）和控制论（cybernetic）

[控制论](https://zhida.zhihu.com/search?content_id=651097658&content_type=Answer&match_order=1&q=%E6%8E%A7%E5%88%B6%E8%AE%BA&zhida_source=entity)算是一种哲学思想，认为自然界一切事物都是两种力量抗衡的结果，一种力量为原动力，另一种力量为约束力。

控制论的含义就是合理利用约束力来指导原动力的作用方向。

这就是抽象层面的解释。

不过，可能很多人看不懂，所以有了各种具体实践。

[工程控制论](https://zhida.zhihu.com/search?content_id=651097658&content_type=Answer&match_order=1&q=%E5%B7%A5%E7%A8%8B%E6%8E%A7%E5%88%B6%E8%AE%BA&zhida_source=entity)，核心为[参数空间](https://zhida.zhihu.com/search?content_id=651097658&content_type=Answer&match_order=1&q=%E5%8F%82%E6%95%B0%E7%A9%BA%E9%97%B4&zhida_source=entity)中的曲线拟合技术，即把一个工程系统分解为多个具体参数构成的数学系统，这些参数所成数学空间为[状态空间](https://zhida.zhihu.com/search?content_id=651097658&content_type=Answer&match_order=1&q=%E7%8A%B6%E6%80%81%E7%A9%BA%E9%97%B4&zhida_source=entity)，参数的预期变化轨迹为参数空间中的曲线，控制系统为拟合拟合这条曲线的[微分方程](https://zhida.zhihu.com/search?content_id=651097658&content_type=Answer&match_order=1&q=%E5%BE%AE%E5%88%86%E6%96%B9%E7%A8%8B&zhida_source=entity)，之所以是微分方程，是因为力学规律，电学规律都是以二阶微分方程形式给出的，是物理学的要求。具体的工程控制论的实践就是参数化，曲线描述，曲线拟合，当然，可以推广到任意维曲面，使用的数学工具也随不同的拟合方法而区别，最简单的就是线性微分方程，线性微分方程组，对于非线性微分方程组，需要考虑解空间的几何特征，也就是[流形](https://zhida.zhihu.com/search?content_id=651097658&content_type=Answer&match_order=1&q=%E6%B5%81%E5%BD%A2&zhida_source=entity)，微分几何，李群之类的。其实，和机器学习与人工智能很像，所以控制论与机器学习往往会结合在一起。

用抽象语言描述，工程系统的原动力为物理规律，约束力为物理参数，通过限制和调整物理参数范围，可以指导物理规律的作用方向。

社会管理，将社会视为复杂系统，提取主要部分参数化，同样获得参数空间，仿照工程控制论进行参数控制，不过，问题出现在社会运行规律非常复杂，是时变的大规模参数依赖的难以预知的，所以，到现在为止，只具有理论上的意义，实际问题还是按照经验处理的。

第三个是人的生命与意识视为复杂系统，这个就远远超越了当前科学的能力。

具体的可以看钱学森的相关论著，钱学森是工程控制论的建立者，非常厉害，前期主要关注工程领域实践，后期，他试图把控制论思想推广到社会系统，科学系统，生命系统，意识系统，由此形成了[系统科学](https://zhida.zhihu.com/search?content_id=651097658&content_type=Answer&match_order=1&q=%E7%B3%BB%E7%BB%9F%E7%A7%91%E5%AD%A6&zhida_source=entity)的划分不过，受制于科学技术水平与群体认知水平，无法实现。但是也留下了大量预见。

也是挺遗憾的，如果能理解钱对于科学研究整体方向的判断与预测，对科学与技术的发展，那真的是洞若观火。所以，他也被称为[战略科学家](https://zhida.zhihu.com/search?content_id=651097658&content_type=Answer&match_order=1&q=%E6%88%98%E7%95%A5%E7%A7%91%E5%AD%A6%E5%AE%B6&zhida_source=entity)，即指引科学前进方向的人。

不过，现在来看的话，参数空间描述有很大的缺陷，他是一种外部性描述，就像高维欧氏空间一样，是一种参数流形的嵌入观点，所以，很快就会遇到算力问题，复杂度过高。目前数学上的观点是[内蕴几何](https://zhida.zhihu.com/search?content_id=651097658&content_type=Answer&match_order=1&q=%E5%86%85%E8%95%B4%E5%87%A0%E4%BD%95&zhida_source=entity)，即从参数依赖关系出发，定义流形的内蕴几何，尽可能降低参数的数目，这就是哈密顿力学中的[辛几何](https://zhida.zhihu.com/search?content_id=651097658&content_type=Answer&match_order=1&q=%E8%BE%9B%E5%87%A0%E4%BD%95&zhida_source=entity)，[切触几何](https://zhida.zhihu.com/search?content_id=651097658&content_type=Answer&match_order=1&q=%E5%88%87%E8%A7%A6%E5%87%A0%E4%BD%95&zhida_source=entity)，广义相对论中的[黎曼几何](https://zhida.zhihu.com/search?content_id=651097658&content_type=Answer&match_order=1&q=%E9%BB%8E%E6%9B%BC%E5%87%A0%E4%BD%95&zhida_source=entity)观点，由此导向几何力学的发展方向，物理定律定义几何关系，物理学为几何学，物理量为几何性质。推广形式为拓扑力学，拓扑物理学，以至于范畴物理学。

当然，最后一段属于非常深刻的角度，属于理论研究的范畴，具体应用或许在几百年之后。

