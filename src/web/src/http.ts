import { Config } from "@/config";
import { GraphQLClient } from "graphql-request";
import { getSdk } from "@/generated/graphql";

export * from "./entity";

export function getApi(headers: { [index: string]: string }) {
    const gqlc = new GraphQLClient(Config.baseUrl + "/graphql", {
        headers: headers,
    });
    return getSdk(gqlc);
}

// Annoying here just to support the same Websockets protocol the
// server (Ariadne) is using.
import { ApolloClient, InMemoryCache } from "@apollo/client";
import { WebSocketLink } from "@apollo/client/link/ws";
import { SubscriptionClient } from "subscriptions-transport-ws";
// import { createClient } from "graphql-ws"; // Not supported by our server.
import gql from "graphql-tag";

function getWebsocketsUrl() {
    const http = Config.baseUrl + "/graphql";
    return http.replace("https", "ws").replace("http", "ws");
}

type OnReceivedFunc = (item: unknown) => Promise<void>;

export async function subscribe(headers: { [index: string]: string }, onReceived: OnReceivedFunc) {
    const wsUrl = getWebsocketsUrl();
    const subscriptionClient = new SubscriptionClient(wsUrl, {
        reconnect: true,
    });

    const link = new WebSocketLink(subscriptionClient);
    const cc = new ApolloClient({
        link: link,
        cache: new InMemoryCache(),
    });

    const asGql = gql`
        subscription {
            nearby(evaluator: "jlewallen")
        }
    `;

    const s = cc.subscribe({
        query: asGql,
    });

    s.subscribe({
        next: ({ data }: { data: unknown }) => {
            return onReceived(data);
        },
    });
}
