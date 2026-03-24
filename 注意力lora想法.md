* 注意力机制中，输入的图像 Patch 序列 $X \in \mathbb{R}^{N \times d}$会被投影为查询（Query）、键（Key）和值（Value）：
  $$Q = XW_q, \quad K = XW_k, \quad V = XW_v$$,
* 水印信息 $w$ 映射为一个微小的权重扰动 $\Delta W(w)$,把这个扰动加到 $W_v$ 上
    $$W_v' = W_v + \alpha \cdot \Delta W(w)$$
* 带水印的矩阵变为
 $$V_{watermarked} = X W_v' = X(W_v + \alpha \cdot \Delta W(w)) = XW_v + \alpha \cdot X\Delta W(w)$$
* 如果当前计算的是“猫耳朵”的 Patch（$x_{ear}$），水印的表现形式是 $x_{ear}\Delta W(w)$。如果计算的是“猫尾巴”的 Patch（$x_{bg}$），水印的表现形式是 $x_{bg}\Delta W(w)$，
* 将水印与语义绑定在一起，把水印当作高价值特征
