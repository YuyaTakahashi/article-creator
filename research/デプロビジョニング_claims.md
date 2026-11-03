# 出典台帳：デプロビジョニング（Deprovisioning）

C01 | デプロビジョニングは、従業員のライフサイクルのうち、ソフトウェアやネットワークサービスへのアクセス権を取り上げる段階である | https://www.techtarget.com/searchsecurity/definition/Deprovisioning | "Deprovisioning is the part of the employee lifecycle in which access rights to software and network services are taken away."
C02 | デプロビジョニングは、従業員が退職したときや社内で役割が変わったときに行われる | https://www.techtarget.com/searchsecurity/definition/Deprovisioning | "Deprovisioning typically occurs when an employee leaves a company or changes roles within an organization."
C03 | デプロビジョニングはプロビジョニングの逆にあたる | https://www.techtarget.com/searchsecurity/definition/Deprovisioning | "It is the opposite of provisioning"
C04 | デプロビジョニングはオフボーディング（退職時の手続き）の中で行われる | https://www.techtarget.com/searchsecurity/definition/Deprovisioning | "Deprovisioning occurs during the offboarding process."
C05 | デプロビジョニングでは、ファイルサーバー・個々のパソコン・認証サーバーにある個人のアカウントを消す | https://www.techtarget.com/searchsecurity/definition/Deprovisioning | "deprovisioning removes individual accounts on file servers, single machines and authentication servers"
C06 | （働き）元従業員が社内の資源に入れないようにするだけでなく、ディスク容量・ポート・証明書・会社支給のパソコンを次に使えるよう空ける | https://www.techtarget.com/searchsecurity/definition/Deprovisioning | "In addition to preventing former employees from accessing corporate resources" / "deprovisioning also frees up disk space, ports, certificates and company-issued computers for future use"
C07 | デプロビジョニングの過程では、誰が承認したか・いつ行ったか・何をしたかを記録して残すべきである | https://www.techtarget.com/searchsecurity/definition/Deprovisioning | "Organizations should audit and keep track of information during the deprovisioning process." / "who authorized the deprovisioning, the date deprovisioning occurred and what actions were taken"
C08 | 一部の組織は、監査の際に復元できるよう、デプロビジョニングしたアカウントを短期間保管する | https://www.techtarget.com/searchsecurity/definition/Deprovisioning | "some organizations save deprovisioned accounts for a short period of time"
C09 | （結果）Beyond Identity社の調査では、デジタルのアクセスを持ち続けた元従業員の56%が、それを使って元の雇用主に損害を与えたと答えた | https://www.techtarget.com/searchsecurity/definition/Deprovisioning | "found that 56% of employees who retained digital access said they used it to harm their former employer"
C10 | デプロビジョニングは、もう必要としない、または使う許可がなくなった利用者のアクセス権を取り消すプロセスである | https://saviynt.com/glossary-listing/deprovisioning | "Deprovisioning refers to the process of revoking access rights" / "for a user who no longer needs them or is no longer authorized to use them."
C11 | デプロビジョニングには、アカウントの無効化、特定の資源へのアクセスの取り消し、認証情報と個人データの削除が含まれうる | https://saviynt.com/glossary-listing/deprovisioning | "Deprovisioning may involve disabling a user's account, revoking their access to specific resources or systems," / "and removing their credentials and personal data to ensure they can no longer access any protected resources."
C12 | 退職時のほか、特定の資源へのアクセスが不要になったとき、セキュリティ侵害で特定の利用者のアクセスを取り消す必要があるときにも行う | https://saviynt.com/glossary-listing/deprovisioning | "IT admins typically perform deprovisioning when an employee leaves the company," / "when their access to certain resources is no longer required," / "or when a security breach requires revoking access for a specific user."
C13 | 不正アクセスや情報漏えいの危険を小さくするために行う | https://saviynt.com/glossary-listing/deprovisioning | "to minimize the risk of unauthorized access or data breaches."
C14 | 自動化ツールで、アカウントの無効化やアクセスの取り消しを管理・追跡することが勧められている | https://saviynt.com/glossary-listing/deprovisioning | "Use automation tools to help manage and track the deprovisioning process," / "including tasks such as disabling user accounts and revoking access to resources."
C15 | （応用例）ID管理サービスの自動デプロビジョニングは、人がチームや組織を離れたとき、該当するシステムのアカウントを自動で無効にする | https://learn.microsoft.com/en-us/entra/identity/app-provisioning/user-provisioning | "Automate deprovisioning: Automatically deactivate accounts in the right systems when people leave the team or organization."
C16 | 手作業でアカウントを作ったり毎週CSVを上げたりする運用は、時間がかかり、費用がかさみ、間違いやすい | https://learn.microsoft.com/en-us/entra/identity/app-provisioning/user-provisioning | "These processes are time-consuming, expensive, and error prone."
C17 | 同じ仕組みで、退職した人や役割が変わって特定のアプリが不要になった人をデプロビジョニングする | https://learn.microsoft.com/en-us/entra/identity/app-provisioning/user-provisioning | "Use the same process to deprovision users when they leave the organization or no longer require access to certain apps based on role change."
C18 | 自動化の動機の一つは、退職した人のIDを主要なSaaSアプリから即座に消して組織を守ることである | https://learn.microsoft.com/en-us/entra/identity/app-provisioning/user-provisioning | "Securing your organization by instantly removing users' identities from key SaaS apps when they leave the organization."
C19 | （前提）アプリごとに利用者管理のAPIが違うため、複数アプリでの利用者管理は難しく、SCIMは利用者がアプリに入る・出る・移るための共通の形式を定める | https://learn.microsoft.com/en-us/entra/identity/app-provisioning/user-provisioning | "User management in more than one app is a challenge because every app tries to perform the same actions." / "the System for Cross-domain Identity Management (SCIM) specification provides a common user schema to help users move into, out of, and around apps."
C20 | 自動プロビジョニングの機能には、アプリ側に直接作られたアカウントや持ち主のいないアカウント（オーファンアカウント）を見つける機能がある | https://learn.microsoft.com/en-us/entra/identity/app-provisioning/user-provisioning | "Discover existing users in your application, including local or orphan accounts."
C21 | SCIMのプロトコル（RFC 7644）は2015年9月に標準化過程の文書として出された | https://www.rfc-editor.org/rfc/rfc7644.txt | "Standards Track" / "September 2015"
C22 | SCIMでは利用者の削除をDELETEで要求し、削除後はその利用者に関するすべての操作に404（見つからない）を返さなければならない | https://datatracker.ietf.org/doc/html/rfc7644 | "Clients request resource removal via DELETE." / "MUST return a 404 (Not Found) error code" / "for all operations associated with the previously deleted resource."
C23 | NIST SP 800-53 のAC-2（アカウント管理）は、アカウントの作成・有効化・変更・無効化・削除を定めた手順どおりに行うことを求める | https://www.stigviewer.com/controls/nist-800-53/AC-2 | "Create, enable, modify, disable, and remove accounts in accordance with"
C24 | AC-2は、アカウント管理の手順を人事の退職・異動の手順とそろえることを求める | https://www.stigviewer.com/controls/nist-800-53/AC-2 | "Align account management processes with personnel termination and transfer processes."
C25 | AC-2は、異動・退職したときをアカウントを無効にする条件に挙げている | https://www.stigviewer.com/controls/nist-800-53/AC-2 | "Conditions for disabling or deactivating accounts include" / "when individuals are transferred or terminated"
C26 | （前提）既存記事「プロビジョニング」は、すぐ使えるように準備・設定することを指し、JITプロビジョニングで時間経過後に権限を自動で取り消すことをデプロビジョニングと呼んでいる | https://uxdaystokyo.com/articles/glossary/provisioning/ | 「すぐに使えるように準備・設定すること」「時間が経過すると権限を自動で取り消します。この取り消しがデプロビジョニングです。」

## 読めなかった出典
- https://nhimg.org/glossary/user-deprovisioning/ （403）
- https://nhimg.org/faq/why-do-departed-users-still-retain-access-in-saas-heavy-environments/ （403）
- https://www.helpnetsecurity.com/2017/09/29/inadequate-it-processes/ （405）
- https://www.darkreading.com/vulnerabilities-threats/survey-many-large-enterprises-underestimate-risk-from-terminated-employees （403）
- https://csrc.nist.gov/glossary/term/deprovisioning （404）

## 提唱者
特定の提唱者を示す出典は見つからなかった（業界用語として使われている）。肖像は入れない。
