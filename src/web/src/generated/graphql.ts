import { GraphQLClient } from "graphql-request";
import * as Dom from "graphql-request/dist/types.dom";
import gql from "graphql-tag";

export type Maybe<T> = T | null;
export type Exact<T extends { [key: string]: unknown }> = { [K in keyof T]: T[K] };
export type MakeOptional<T, K extends keyof T> = Omit<T, K> & { [SubKey in K]?: Maybe<T[SubKey]> };
export type MakeMaybe<T, K extends keyof T> = Omit<T, K> & { [SubKey in K]: Maybe<T[SubKey]> };
/** All built-in and custom scalars, mapped to their actual values */
export type Scalars = {
    ID: string;
    String: string;
    Boolean: boolean;
    Int: number;
    Float: number;
    Auth: any;
    JsonDiff: any;
    Key: any;
    Reply: any;
    SerializedEntity: any;
};

export type Credentials = {
    username: Scalars["String"];
    password: Scalars["String"];
    token?: Maybe<Scalars["String"]>;
};

export type EntitiesUpdated = {
    __typename?: "EntitiesUpdated";
    affected?: Maybe<Array<KeyedEntity>>;
};

export type EntityDiff = {
    key: Scalars["String"];
    serialized: Scalars["String"];
};

export type EntityTemplate = {
    name: Scalars["String"];
    desc: Scalars["String"];
    klass: Scalars["String"];
    key?: Maybe<Scalars["String"]>;
    holding?: Maybe<Array<Scalars["Key"]>>;
};

export type Evaluation = {
    __typename?: "Evaluation";
    reply: Scalars["Reply"];
    entities?: Maybe<Array<KeyedEntity>>;
};

export type KeyedEntity = {
    __typename?: "KeyedEntity";
    key: Scalars["String"];
    serialized: Scalars["SerializedEntity"];
    diff?: Maybe<Scalars["JsonDiff"]>;
};

export type LanguageQueryCriteria = {
    text: Scalars["String"];
    evaluator: Scalars["Key"];
    reach?: Maybe<Scalars["Int"]>;
    subscription?: Maybe<Scalars["Boolean"]>;
    persistence?: Maybe<PersistenceCriteria>;
};

export type Mutation = {
    __typename?: "Mutation";
    login: Scalars["Auth"];
    makeSample?: Maybe<EntitiesUpdated>;
    update?: Maybe<EntitiesUpdated>;
    language: Evaluation;
    create: Evaluation;
};

export type MutationLoginArgs = {
    credentials: Credentials;
};

export type MutationUpdateArgs = {
    entities?: Maybe<Array<EntityDiff>>;
};

export type MutationLanguageArgs = {
    criteria: LanguageQueryCriteria;
};

export type MutationCreateArgs = {
    entities?: Maybe<Array<EntityTemplate>>;
};

export type PersistenceCriteria = {
    read: Scalars["String"];
    write: Scalars["String"];
};

export type Query = {
    __typename?: "Query";
    size: Scalars["Int"];
    world: KeyedEntity;
    entities?: Maybe<Array<KeyedEntity>>;
    entitiesByKey?: Maybe<Array<KeyedEntity>>;
    entitiesByGid?: Maybe<Array<KeyedEntity>>;
    areas?: Maybe<Array<KeyedEntity>>;
    people?: Maybe<Array<KeyedEntity>>;
};

export type QueryEntitiesArgs = {
    keys?: Maybe<Array<Scalars["Key"]>>;
    reach?: Maybe<Scalars["Int"]>;
    identities?: Maybe<Scalars["Boolean"]>;
};

export type QueryEntitiesByKeyArgs = {
    key?: Maybe<Scalars["Key"]>;
    reach?: Maybe<Scalars["Int"]>;
    identities?: Maybe<Scalars["Boolean"]>;
};

export type QueryEntitiesByGidArgs = {
    gid?: Maybe<Scalars["Int"]>;
    reach?: Maybe<Scalars["Int"]>;
    identities?: Maybe<Scalars["Boolean"]>;
};

export type Subscription = {
    __typename?: "Subscription";
    nearby?: Maybe<Array<Scalars["Reply"]>>;
};

export type SubscriptionNearbyArgs = {
    evaluator?: Maybe<Scalars["Key"]>;
};

export type LoginMutationVariables = Exact<{
    username: Scalars["String"];
    password: Scalars["String"];
}>;

export type LoginMutation = { __typename?: "Mutation" } & Pick<Mutation, "login">;

export type RedeemInviteMutationVariables = Exact<{
    username: Scalars["String"];
    password: Scalars["String"];
    token: Scalars["String"];
}>;

export type RedeemInviteMutation = { __typename?: "Mutation" } & Pick<Mutation, "login">;

export type LanguageMutationVariables = Exact<{
    text: Scalars["String"];
    evaluator: Scalars["Key"];
}>;

export type LanguageMutation = { __typename?: "Mutation" } & {
    language: { __typename?: "Evaluation" } & Pick<Evaluation, "reply"> & {
            entities?: Maybe<Array<{ __typename?: "KeyedEntity" } & Pick<KeyedEntity, "key" | "serialized" | "diff">>>;
        };
};

export type UpdateEntityMutationVariables = Exact<{
    key: Scalars["String"];
    serialized: Scalars["String"];
}>;

export type UpdateEntityMutation = { __typename?: "Mutation" } & {
    update?: Maybe<
        { __typename?: "EntitiesUpdated" } & {
            affected?: Maybe<Array<{ __typename?: "KeyedEntity" } & Pick<KeyedEntity, "key" | "serialized">>>;
        }
    >;
};

export type AreasQueryVariables = Exact<{ [key: string]: never }>;

export type AreasQuery = { __typename?: "Query" } & {
    areas?: Maybe<Array<{ __typename?: "KeyedEntity" } & Pick<KeyedEntity, "key" | "serialized">>>;
};

export type PeopleQueryVariables = Exact<{ [key: string]: never }>;

export type PeopleQuery = { __typename?: "Query" } & {
    people?: Maybe<Array<{ __typename?: "KeyedEntity" } & Pick<KeyedEntity, "key" | "serialized">>>;
};

export type EntityQueryVariables = Exact<{
    key: Scalars["Key"];
}>;

export type EntityQuery = { __typename?: "Query" } & {
    entitiesByKey?: Maybe<Array<{ __typename?: "KeyedEntity" } & Pick<KeyedEntity, "key" | "serialized">>>;
};

export type NearbySubscriptionVariables = Exact<{ [key: string]: never }>;

export type NearbySubscription = { __typename?: "Subscription" } & Pick<Subscription, "nearby">;

export const LoginDocument = gql`
    mutation login($username: String!, $password: String!) {
        login(credentials: { username: $username, password: $password })
    }
`;
export const RedeemInviteDocument = gql`
    mutation redeemInvite($username: String!, $password: String!, $token: String!) {
        login(credentials: { username: $username, password: $password, token: $token })
    }
`;
export const LanguageDocument = gql`
    mutation language($text: String!, $evaluator: Key!) {
        language(criteria: { text: $text, evaluator: $evaluator, reach: 1, subscription: true }) {
            reply
            entities {
                key
                serialized
                diff
            }
        }
    }
`;
export const UpdateEntityDocument = gql`
    mutation updateEntity($key: String!, $serialized: String!) {
        update(entities: [{ key: $key, serialized: $serialized }]) {
            affected {
                key
                serialized
            }
        }
    }
`;
export const AreasDocument = gql`
    query areas {
        areas {
            key
            serialized
        }
    }
`;
export const PeopleDocument = gql`
    query people {
        people {
            key
            serialized
        }
    }
`;
export const EntityDocument = gql`
    query entity($key: Key!) {
        entitiesByKey(key: $key) {
            key
            serialized
        }
    }
`;
export const NearbyDocument = gql`
    subscription nearby {
        nearby
    }
`;

export type SdkFunctionWrapper = <T>(action: (requestHeaders?: Record<string, string>) => Promise<T>, operationName: string) => Promise<T>;

const defaultWrapper: SdkFunctionWrapper = (action, _operationName) => action();

export function getSdk(client: GraphQLClient, withWrapper: SdkFunctionWrapper = defaultWrapper) {
    return {
        login(variables: LoginMutationVariables, requestHeaders?: Dom.RequestInit["headers"]): Promise<LoginMutation> {
            return withWrapper(
                (wrappedRequestHeaders) =>
                    client.request<LoginMutation>(LoginDocument, variables, { ...requestHeaders, ...wrappedRequestHeaders }),
                "login"
            );
        },
        redeemInvite(variables: RedeemInviteMutationVariables, requestHeaders?: Dom.RequestInit["headers"]): Promise<RedeemInviteMutation> {
            return withWrapper(
                (wrappedRequestHeaders) =>
                    client.request<RedeemInviteMutation>(RedeemInviteDocument, variables, { ...requestHeaders, ...wrappedRequestHeaders }),
                "redeemInvite"
            );
        },
        language(variables: LanguageMutationVariables, requestHeaders?: Dom.RequestInit["headers"]): Promise<LanguageMutation> {
            return withWrapper(
                (wrappedRequestHeaders) =>
                    client.request<LanguageMutation>(LanguageDocument, variables, { ...requestHeaders, ...wrappedRequestHeaders }),
                "language"
            );
        },
        updateEntity(variables: UpdateEntityMutationVariables, requestHeaders?: Dom.RequestInit["headers"]): Promise<UpdateEntityMutation> {
            return withWrapper(
                (wrappedRequestHeaders) =>
                    client.request<UpdateEntityMutation>(UpdateEntityDocument, variables, { ...requestHeaders, ...wrappedRequestHeaders }),
                "updateEntity"
            );
        },
        areas(variables?: AreasQueryVariables, requestHeaders?: Dom.RequestInit["headers"]): Promise<AreasQuery> {
            return withWrapper(
                (wrappedRequestHeaders) =>
                    client.request<AreasQuery>(AreasDocument, variables, { ...requestHeaders, ...wrappedRequestHeaders }),
                "areas"
            );
        },
        people(variables?: PeopleQueryVariables, requestHeaders?: Dom.RequestInit["headers"]): Promise<PeopleQuery> {
            return withWrapper(
                (wrappedRequestHeaders) =>
                    client.request<PeopleQuery>(PeopleDocument, variables, { ...requestHeaders, ...wrappedRequestHeaders }),
                "people"
            );
        },
        entity(variables: EntityQueryVariables, requestHeaders?: Dom.RequestInit["headers"]): Promise<EntityQuery> {
            return withWrapper(
                (wrappedRequestHeaders) =>
                    client.request<EntityQuery>(EntityDocument, variables, { ...requestHeaders, ...wrappedRequestHeaders }),
                "entity"
            );
        },
        nearby(variables?: NearbySubscriptionVariables, requestHeaders?: Dom.RequestInit["headers"]): Promise<NearbySubscription> {
            return withWrapper(
                (wrappedRequestHeaders) =>
                    client.request<NearbySubscription>(NearbyDocument, variables, { ...requestHeaders, ...wrappedRequestHeaders }),
                "nearby"
            );
        },
    };
}
export type Sdk = ReturnType<typeof getSdk>;
