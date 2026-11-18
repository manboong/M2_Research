from collections import Counter, defaultdict
from network.construction.replies import component_sizes
from network.metrics.mixing import mixing, null_mixing, ratio


def summarize(comments, edges, issues, users, annotations, samples, seed):
    by_week, edge_week, issue_week = defaultdict(list), defaultdict(list), defaultdict(list)
    for c in comments:
        by_week[c.week].append(c)
    for e in edges:
        edge_week[e.comment.week].append(e)
    for issue in issues:
        issue_week[issue["week"]].append(issue)
    output = []
    for week, records in sorted(by_week.items()):
        replies = edge_week[week]
        authors = {c.user for c in records}
        nodes = authors | {e.target for e in replies}
        articles = defaultdict(set)
        for c in records:
            articles[c.user].add(c.article_key)
        components = component_sizes(nodes, replies)
        activity = Counter(c.user for c in records)
        n_top = max(1, (len(authors) + 99) // 100)
        counts = Counter(i["reason"] for i in issue_week[week])
        candidate_count = sum(c.reply for c in records)
        row = dict(week=week, comments=len(records), authors=len(authors),
                   articles=len({c.article_key for c in records}),
                   multi_article_users=sum(len(a) > 1 for a in articles.values()),
                   multi_article_rate=ratio(sum(len(a) > 1 for a in articles.values()), len(authors)),
                   reply_candidates=candidate_count, reply_edges=len(replies),
                   usable_reply_rate=ratio(len(replies), candidate_count),
                   reply_senders=len({e.source for e in replies}),
                   reply_receivers=len({e.target for e in replies}),
                   network_nodes=len(nodes),
                   external_week_receivers=len(nodes - authors),
                   isolated_nodes=sum(n == 1 for n in components),
                   weak_components=len(components), largest_component=components[0],
                   largest_component_fraction=components[0] / len(nodes),
                   top_one_percent_comment_share=sum(n for _, n in activity.most_common(n_top)) / len(records))
        for reason in ("missing_parent_id", "self_parent_pointer", "parent_not_in_dataset",
                       "parent_after_reply", "self_reply"):
            row[reason] = counts[reason]
        row.update(mixing(replies, users, annotations))
        row.update(null_mixing(replies, users, samples, seed))
        output.append(row)
    return output
