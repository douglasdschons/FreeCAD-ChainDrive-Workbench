# Plano de figuras da nota técnica

As figuras do projeto anterior serão bases de trabalho, não imagens finais imutáveis. Símbolos, casos numéricos, cores e legendas devem ser adaptados à nota do Workbench.

Projeto-base: [chain-drive-geometry-calculator](https://github.com/douglasdschons/chain-drive-geometry-calculator)

| ID | Função na narrativa | Base principal | Adaptação necessária |
|---|---|---|---|
| F01 | Explicar os dois problemas resolvidos: catálogo → CAD e entrecentros discreto | Nova composição; `polygonal_layout_asa80_11_20.png` como elemento central | Acrescentar catálogo simplificado e conjunto FreeCAD atual |
| F02 | Mostrar as três saídas do Workbench | Capturas novas do projeto atual | Sprocket isolada, corrente isolada e conjunto completo com identidade visual comum |
| F03 | Mostrar o fluxo de dados e software | `application.py` e `ARCHITECTURE_INVENTORY.md` | Criar diagrama original catálogo → cálculo → CAD |
| F04 | Identificar dimensões da corrente | Manual iwis p. 9 ou guia Tsubaki | Redesenhar com `p,E,D_R,H,D_G,L,T_p` |
| F05 | Identificar dimensões comerciais da sprocket | Desenho da série em `catalogo_enco.pdf` | Localizar página exata e redesenhar sem reproduzir o scan |
| F06 | Explicar círculo/polígono de passo | `ASAChainDriveApp/docs/figures/sprocket_fig_02_pitch_geometry.pdf` | Uniformizar símbolos com a nota em português |
| F07 | Explicar a estimativa contínua | Formulação em `docs/complete_mathematical_formulation_en.tex` do projeto antigo | Redesenhar raios, tangentes, envolvimentos e `C` |
| F08 | Comparar topologia de contato par e ímpar | `polygonal_layout_asa80_11_20.png` e `polygonal_layout_asa80_19_20.png` | Destacar `M`, `M-1`, eixo de simetria e intervalos de passo |
| F09 | Mostrar corda rígida versus incremento no caminho | Novo gráfico do solver atual | Usar estética dos antigos `plot_1.png` e `plot_2.png` |
| F10 | Resumir o algoritmo de entrecentros | Solver atual + formulação antiga | Fluxograma com estimativa, candidatos `N`, caminhada, raiz e seleção |
| F11 | Explicar coordenadas solver/FreeCAD | `cad/chain_generator.py` | Criar eixos `(x,y)` e `(X,Y,Z)`, rotação `-Y`, JointA/B |
| F12 | Mostrar InnerLink | `ASA80_InnerLink.FCStd` | Captura explodida e cotada |
| F13 | Mostrar OuterLink | `ASA80_OuterLink.FCStd` | Captura explodida e cotada |
| F14 | Mostrar OffsetLink e sua reversão na montagem | `ASAChainDriveApp/output/validation/ASA80_OffsetLink_Standalone_*.FCStd` | Acrescentar pin-at-A, roller-at-B e rotação de 180° |
| F15 | Explicar assentamento do rolete | `sprocket_fig_03_seating_curve.pdf`; GEARS pp. 2–4 | Atualizar notação e conferir equações |
| F16 | Explicar construção do vão | `design_draw_sprocket_5.pdf`, Fig. 1 e pp. 3–12 | Redesenhar `a,b,c,x,y,z,L` conforme escolhas reais do código |
| F17 | Mostrar o conjunto canônico atual | Nova captura ASA80 11/20/400 | Indicar `C_d`, `C_N`, rodas, corrente e OffsetLink |
| F18 | Validar cálculo contra CAD | Pares antigos `plot_1.png`/`cd_1.png` e `plot_2.png`/`cd_2.png` | Recriar o mesmo formato para o caso atual 11/20/400 e demais casos escolhidos |

## Arquivos recuperados do projeto anterior

- `docs/figures/polygonal_layout_asa80_11_20.png`
- `docs/figures/polygonal_layout_asa80_19_20.png`
- `docs/figures/plot_1.png`
- `docs/figures/plot_2.png`
- `docs/figures/cd_1.png`
- `docs/figures/cd_2.png`
- `docs/complete_mathematical_formulation_en.tex`
- `docs/complete_mathematical_formulation_en.pdf`

## Regra editorial

Não copiar páginas completas de normas ou catálogos. As figuras finais devem ser diagramas autorais reconstruídos ou capturas dos modelos produzidos pelo próprio Workbench. Toda figura derivada deve manter em seus arquivos de trabalho a indicação da fonte e página consultadas.
