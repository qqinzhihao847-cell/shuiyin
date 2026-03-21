## AdLaN公式 
$$AdaLN(x) = f(c, t) \odot LayerNorm(x) + g(c, t)$$
### 如果直接将水印信息当做像prompt和时间步一样的条件注入，可能会有的情况:
* 注入水印信号后可能会造成某些通道产生Massive Activations(极少部分的隐藏层特征维度会产生数值极其巨大的激活值，这些维度是特定的，这些值可能比正常的激活值大几十倍甚至上百倍)，此时如果采用论文*Unleashing Diffusion Transformers for Visual Correspondence by Modulating Massive Activations*中的方法，
把水印对通道的影响进行消除(除以某个系数或者通道丢弃），水印信息就被抹除了。
