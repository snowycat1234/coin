# 2022 mark 原始源恢复搜索结论

完整2022 December mark月ZIP仍缺5个，July12/13真实mark分钟仍缺27个。2022原生源门维持BLOCKED_SOURCE。此次已知December31日档的本地保存不替代月档，不构成新的全年覆盖改善。

## 有界检查范围

- 92个公开分支；1,027个可达commit；6,364个Git tree；21,599个历史blob/path版本
- 46个相关源索引，实际Git blob身份全部核验；此前全仓archive目录索引SHA也已回读核验
- 本地175个ZIP、30,583个central-directory成员；10个本地thin bundle中2个可列完整树，8个缺delta base
- 一个系统目录无读取权限；未申请或绕过权限。不能断言thin bundle完整body、不可达Git对象、旧机器或外部存储中没有原字节

此前已知的five-contract 2022-12-31 mark daily ZIP和CHECKSUM共143,023 bytes现已从一个明确引用的983,659-byte公开源包保存并独立检查：7,200行、SHA、原CHECKSUM文本、CRC、12字段、准确UTC分钟网格与OHLC一致性通过。原BOUNDARY.json也明确full2022Dec_certified=false。原source字节已公开，本分支不重复上传。

[原公开Dec31源包索引](https://github.com/snowycat1234/coin/blob/c63a936b7422f7dbf33f6234acebfb02a3b1f3c6/research/mark-trade-dislocation-20261012/public/INPUTS/INDEX.json)

## 精确带回清单

- [官方文件路径、旧hash/size与验收步骤](OFFICIAL_FILES_TO_RETURN.json)
- [27个缺失分钟的UTC/open-ms CSV](JULY_MARK_ROWS_TO_RETURN.csv)
- [人工检查清单](SOURCE_RETURN_CHECKLIST.md)
- [完整有限搜索结果和限制](SOURCE_SEARCH_RESULT.json)
- [已知Dec31真实原字节本地核验](KNOWN_DEC31_LOCAL_RECOVERY.json)
- [结果及支持索引身份hash](SOURCE_EVIDENCE_HASHES.json)

相同July官方月/日档的重新下载不能修复原来的27个洞。trade、index、premium、5分钟聚合、稀疏daily checkpoint和模型mark均不得替代真实1分钟mark观测。未来带回官方原字节后仍须做完整grid、冻结trade daily-close parity和funding chronology验证，再另行决定金融准入。

此次没有provider请求、2026受保护原始body读取、新云任务、Library使用、targets、fit或钱包。扫描在没有新的明确target-body候选后停止。
