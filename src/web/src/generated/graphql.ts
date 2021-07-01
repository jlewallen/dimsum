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
    JsonDiff: any;
    Key: any;
    Reply: any;
    SerializedEntity: any;
    Token: any;
};

export type Credentials = {
    username: Scalars["String"];
    password: Scalars["String"];
};

export type EntitiesUpdated = {
    __typename?: "EntitiesUpdated";
    affected: Scalars["Int"];
};

export type EntityDiff = {
    key: Scalars["String"];
    serialized: Scalars["String"];
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
    persistence?: Maybe<PersistenceCriteria>;
};

export type Mutation = {
    __typename?: "Mutation";
    login: Scalars["Token"];
    makeSample?: Maybe<EntitiesUpdated>;
    update?: Maybe<EntitiesUpdated>;
    language: Evaluation;
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

export type PersistenceCriteria = {
    read: Scalars["String"];
    write: Scalars["String"];
};

export type Query = {
    __typename?: "Query";
    size: Scalars["Int"];
    world: KeyedEntity;
    entitiesByKey?: Maybe<Array<KeyedEntity>>;
    entitiesByGid?: Maybe<Array<KeyedEntity>>;
    areas?: Maybe<Array<KeyedEntity>>;
    people?: Maybe<Array<KeyedEntity>>;
};

export type QueryEntitiesByKeyArgs = {
    key?: Maybe<Scalars["Key"]>;
    identities?: Maybe<Scalars["Boolean"]>;
};

export type QueryEntitiesByGidArgs = {
    gid?: Maybe<Scalars["Int"]>;
    identities?: Maybe<Scalars["Boolean"]>;
};

export type LoginMutationVariables = Exact<{
    username: Scalars["String"];
    password: Scalars["String"];
}>;

export type LoginMutation = { __typename?: "Mutation" } & Pick<Mutation, "login">;

export type LanguageMutationVariables = Exact<{
    text: Scalars["String"];
    evaluator: Scalars["Key"];
}>;

export type LanguageMutation = { __typename?: "Mutation" } & {
    language: { __typename?: "Evaluation" } & Pick<Evaluation, "reply"> & {
            entities?: Maybe<Array<{ __typename?: "KeyedEntity" } & Pick<KeyedEntity, "key" | "serialized" | "diff">>>;
        };
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

export const LoginDocument = gql`
    mutation login($username: String!, $password: String!) {
        login(credentials: { username: $username, password: $password })
    }
`;
export const LanguageDocument = gql`
    mutation language($text: String!, $evaluator: Key!) {
        language(criteria: { text: $text, evaluator: $evaluator }) {
            reply
            entities {
                key
                serialized
                diff
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
        language(variables: LanguageMutationVariables, requestHeaders?: Dom.RequestInit["headers"]): Promise<LanguageMutation> {
            return withWrapper(
                (wrappedRequestHeaders) =>
                    client.request<LanguageMutation>(LanguageDocument, variables, { ...requestHeaders, ...wrappedRequestHeaders }),
                "language"
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
    };
}
export type Sdk = ReturnType<typeof getSdk>;
